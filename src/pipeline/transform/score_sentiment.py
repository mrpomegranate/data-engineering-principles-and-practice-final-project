"""
Score sentiment: fill sentiment_label / sentiment_score on headline_fact.

Incremental by design — only touches rows WHERE sentiment_score IS NULL,
so re-runs score just the newly loaded headlines. VADER's compound score
(-1.0 .. +1.0) maps to labels using its standard thresholds:

    compound >=  0.05  -> positive
    compound <= -0.05  -> negative
    otherwise          -> neutral

Run standalone (scores ALL unscored headlines, any ticker):
    python -m src.pipeline.transform.score_sentiment
"""

from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from ..extract.run_logger import log_run
from ..load.warehouse import get_connection

load_dotenv(override=True)

BATCH_SIZE = 1000

UPDATE_SQL = """
    UPDATE headline_fact
    SET sentiment_score = %s,
        sentiment_label = %s
    WHERE headline_id = %s
"""


def label_for(compound: float) -> str:
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "neutral"


def score() -> int:
    """Score every unscored headline. Returns rows updated."""
    analyzer = SentimentIntensityAnalyzer()
    conn = get_connection()
    total = 0
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    try:
        while True:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT headline_id, headline_text FROM headline_fact "
                    "WHERE sentiment_score IS NULL LIMIT %s",
                    (BATCH_SIZE,),
                )
                batch = cur.fetchall()
            if not batch:
                break

            updates = []
            for headline_id, text in batch:
                compound = analyzer.polarity_scores(text)["compound"]
                lbl = label_for(compound)
                counts[lbl] += 1
                updates.append((round(compound, 4), lbl, headline_id))

            with conn.cursor() as cur:
                cur.executemany(UPDATE_SQL, updates)
            conn.commit()
            total += len(updates)
            print(f"  scored {total} headlines...", flush=True)

        log_run("transform", "vader", "success",
                extracted=total, loaded=total)
    except Exception as exc:
        conn.rollback()
        log_run("transform", "vader", "failure", error=str(exc))
        raise
    finally:
        conn.close()

    print(f"sentiment scoring: {total} headlines scored "
          f"({counts['positive']} positive, {counts['neutral']} neutral, "
          f"{counts['negative']} negative)")
    return total


if __name__ == "__main__":
    score()