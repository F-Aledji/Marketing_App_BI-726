# Tracking Logger
# Loggt alle API-Calls für das Entwickler-Dashboard

import os
import csv
from datetime import datetime
from typing import Optional

DATA_DIR = "data"
TRACKING_FILE = os.path.join(DATA_DIR, "tracking_logs.csv")

# CSV-Header für das Tracking-Log (mit Token-Tracking)
TRACKING_COLUMNS = [
    "timestamp",
    "dateiname",
    "provider",
    "batch_nummer",
    "batch_total",
    "anzahl_eintraege",
    "dauer_sekunden",
    "status",
    "input_tokens",
    "output_tokens",
    "fehler_msg"
]


def log_api_call(
    dateiname: str,
    provider: str,
    batch_nummer: int,
    batch_total: int,
    anzahl_eintraege: int,
    dauer_sekunden: float,
    status: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    fehler_msg: Optional[str] = None
) -> None:
    """
    Loggt einen API-Call in die Tracking-Datei.
    
    Args:
        dateiname: Name der verarbeiteten PDF
        provider: Name des KI-Providers
        batch_nummer: Aktueller Batch (1-basiert)
        batch_total: Gesamtanzahl Batches
        anzahl_eintraege: Anzahl Einträge in diesem Batch
        dauer_sekunden: Verarbeitungsdauer
        status: "success" oder "error"
        input_tokens: Verbrauchte Input-Tokens
        output_tokens: Verbrauchte Output-Tokens
        fehler_msg: Optional, Fehlermeldung bei status="error"
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    
    file_exists = os.path.exists(TRACKING_FILE)
    
    with open(TRACKING_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        if not file_exists:
            writer.writerow(TRACKING_COLUMNS)
        
        writer.writerow([
            datetime.now().isoformat(),
            dateiname,
            provider,
            batch_nummer,
            batch_total,
            anzahl_eintraege,
            round(dauer_sekunden, 2),
            status,
            input_tokens,
            output_tokens,
            fehler_msg or ""
        ])


def get_tracking_stats() -> dict:
    """
    Liest die Tracking-Logs und berechnet Statistiken.
    
    Returns:
        Dict mit Statistiken für das Dashboard
    """
    if not os.path.exists(TRACKING_FILE):
        return {
            "total_calls": 0,
            "success_rate": 0.0,
            "avg_duration": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "logs": []
        }
    
    logs = []
    with open(TRACKING_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        logs = list(reader)
    
    if not logs:
        return {
            "total_calls": 0,
            "success_rate": 0.0,
            "avg_duration": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "logs": []
        }
    
    total = len(logs)
    successes = sum(1 for log in logs if log.get("status") == "success")
    
    # Sichere Konvertierung
    durations = []
    total_input = 0
    total_output = 0
    
    for log in logs:
        try:
            val = log.get("dauer_sekunden", "")
            if val and val != "dauer_sekunden":
                durations.append(float(val))
        except (ValueError, TypeError):
            pass
        
        try:
            total_input += int(log.get("input_tokens", 0) or 0)
            total_output += int(log.get("output_tokens", 0) or 0)
        except (ValueError, TypeError):
            pass
    
    return {
        "total_calls": total,
        "success_rate": round((successes / total) * 100, 1) if total > 0 else 0.0,
        "avg_duration": round(sum(durations) / len(durations), 2) if durations else 0.0,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "logs": logs[-50:]
    }
