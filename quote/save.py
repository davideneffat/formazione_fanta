import logging
import pandas as pd
from quote.config import ProcessedData


def save_all_quotes_to_dataframe(scraped_data: ProcessedData):
    """
    Crea un DataFrame pandas con tutte le quote di gol e assist e lo salva in un file CSV.
    """
    logging.info("Creazione del DataFrame con tutte le quote dei giocatori...")

    try:
        # 1. Creare un DataFrame per i marcatori
        scorers_list = [
            {"player_name": p.player_name, "prob_goal": 100 / p.quote if p.quote > 0 else 0}
            for p in scraped_data.scorers
        ]
        df_scorers = pd.DataFrame(scorers_list)

        # 2. Creare un DataFrame per gli assist
        assists_list = [
            {"player_name": p.player_name, "prob_assist": 100 / p.quote if p.quote > 0 else 0}
            for p in scraped_data.assists
        ]
        df_assists = pd.DataFrame(assists_list)

        # 3. Unire i due DataFrame
        # Usiamo un merge 'outer' per assicurarci di includere tutti i giocatori,
        # anche quelli che hanno solo una quota gol o solo una quota assist.
        if not df_scorers.empty and not df_assists.empty:
            df_merged = pd.merge(df_scorers, df_assists, on="player_name", how="outer")
        elif not df_scorers.empty:
            df_merged = df_scorers
            df_merged['prob_assist'] = 0  # Aggiunge la colonna mancante
        elif not df_assists.empty:
            df_merged = df_assists
            # Se esiste solo il df assist, dobbiamo aggiungere la colonna goal
            df_merged['prob_goal'] = 0
            # E riordinare le colonne per coerenza
            df_merged = df_merged[['player_name', 'prob_goal', 'prob_assist']]
        else:
            logging.warning("Nessun dato su marcatori o assist da salvare nel DataFrame.")
            return

        # 4. Pulizia e ordinamento
        # Sostituisce i valori NaN (generati dal merge) con 0
        df_merged = df_merged.fillna(0)
        # Arrotonda le probabilità a 2 cifre decimali
        df_merged['prob_goal'] = df_merged['prob_goal'].round(2)
        df_merged['prob_assist'] = df_merged['prob_assist'].round(2)
        # Ordina il DataFrame per probabilità di gol decrescente
        df_merged = df_merged.sort_values(by="prob_goal", ascending=False)

        # 5. Salvataggio su file CSV
        filename = "quote_giornata.csv"
        # 'utf-8-sig' aiuta Excel ad aprire correttamente i file con caratteri speciali
        df_merged.to_csv(filename, index=False, encoding='utf-8-sig')
        
        logging.info(f"DataFrame con {len(df_merged)} giocatori salvato con successo in '{filename}'")

    except Exception as e:
        logging.error(f"Errore durante la creazione o il salvataggio del DataFrame: {e}", exc_info=True)
