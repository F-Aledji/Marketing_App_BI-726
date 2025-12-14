Sehr gerne! Hier ist eine detaillierte Dokumentation aller Funktionen im core-Ordner als Markdown. Du kannst diese Datei z.B. als DOCUMENTATION.md in deinem Projekt speichern oder die Erklärungen direkt als Docstrings in deinen Code kopieren.

Core Dokumentation
Dieses Modul (core/) enthält die gesamte Logik für das Extrahieren, Analysieren und Exportieren von Artikelnummern.

1. Konfiguration (
core/config.py
)
Diese Datei definiert die Regeln und das Aussehen der Anwendung.

get_config()
Was: Lädt die dynamische Konfiguration (Blacklisten für Nummern und Präfixe) aus einer externen JSON-Datei.
Warum: Damit du Blacklisten bearbeiten kannst, ohne den Programmcode ändern zu müssen.
Wann: Wird zu Beginn fast jeder Analyse-Funktion aufgerufen, um die aktuellen Regeln zu laden.
get_column_config()
Was: Definiert, wie die Spalten (Seite, Artikelnummer, Kontext) im Streamlit-Frontend dargestellt werden.
Warum: Standard-Tabellen in Streamlit sehen oft langweilig aus oder sind falsch formatiert. Hiermit setzen wir Breiten und Datentypen fest.
Wann: Wird im Frontend (B.nr. Suche.py) aufgerufen, kurz bevor die Tabellen (st.dataframe) gezeichnet werden.
2. Analysatoren (
core/analyzers.py
)
Hier sitzt die "Intelligenz", die entscheidet, ob ein Treffer gut oder schlecht ist.

get_clean_string(p1, p2, p3)
Was: Eine kleine Hilfsfunktion, die die drei Teile einer Nummer (z.B. "AB", "123", "45") zu einem String zusammenfügt ohne Leerzeichen ("AB12345").
Warum: Um Nummern leichter vergleichbar zu machen und in Listen zu suchen.
Wann: Wird intern von 
check_plausibility
 genutzt.
check_plausibility(match_tuple, config)
Was: Der "Türsteher". Prüft harte Ausschlusskriterien:
Beginnt die Nummer mit "0"? (Oft Telefonvorwahlen)
Ist es ein Jahr (2023-2026)?
Steht die Nummer auf der Blacklist?
Hat sie ein verbotenes Präfix?
Warum: Um offensichtlichen Müll sofort auszusortieren, bevor wir Rechenleistung für Kontext-Analysen verschwenden.
Wann: Wird für jeden Regex-Treffer sofort als allererstes aufgerufen.
analyze_context(text, match_start, match_end, config)
Was: Der "Detektiv". Schaut sich den Text 35 Zeichen vor und nach der Nummer an. Es berechnet Distanzen zu "bösen Wörtern" (z.B. "Telefon", "Fax") und "guten Wörtern" (z.B. "Bestell-Nr").
Warum: Eine Nummer wie "040 123 45" ist technisch valide, aber wenn das Wort "Telefon" davor steht, ist es keine Artikelnummer.
Wann: Wird aufgerufen, nachdem 
check_plausibility
 sein "Okay" gegeben hat.
check_ocr_quality(pdf_bytes)
Was: Liest die ersten 3 Seiten und zählt die Zeichen.
Warum: Um den User zu warnen, wenn er ein gescanntes Bild hochlädt (wo kein Text extrahierbar ist), anstatt einfach "0 Treffer" anzuzeigen.
Wann: Einmalig ganz am Anfang, direkt nachdem der User eine Datei hochgeladen hat.
3. Extraktoren (
core/extractors.py
)
Der Motor, der das PDF liest und die Rohdaten sammelt.

clean_text(text)
Was: Ersetzt "geschützte Leerzeichen" (\u00A0) durch normale Leerzeichen.
Warum: PDFs enthalten oft seltsame Whitespace-Formatierungen, die Regex-Suchen verwirren können.
Wann: Bevor der Text an die Regex-Suche übergeben wird.
extract_match_groups(match_tuple)
Was: Sortiert die Ergebnisse der Regex-Gruppen. Unsere Regex sucht entweder nach AA 123 45 ODER 12 123 45. Das Ergebnis ist oft ein Tupel mit leeren Werten (z.B. 
("AB","123","45", None, None, None)
). Diese Funktion pickt die richtigen Teile heraus.
Warum: Damit der restliche Code saubere Variablen hat und sich nicht mit Regex-Artefakten herumschlagen muss.
Wann: Innerhalb der Suchschleife für jeden Treffer.
normalize(p1, p2, p3)
Was: Formatiert die gefundene Nummer einheitlich mit Leerzeichen (z.B. "AB 123 45").
Warum: Damit es im Frontend für den Menschen gut lesbar ist.
Wann: Beim Speichern eines Treffers.
extract_matches_from_text(text, page_num, source, config)
Was: Die Arbeitspferd-Funktion. Sie nimmt einen Textblock (eine Seite), führt die Regex-Suche aus, und ruft für jeden Treffer 
check_plausibility
 und 
analyze_context
 auf.
Warum: Um DRY (Don't Repeat Yourself) einzuhalten. Wir rufen diese Logik sowohl für PyMuPDF als auch für pdfplumber auf.
Wann: Für jede Seite des PDFs, einmal pro Engine.
analyze_pdf(uploaded_file)
Was: Der Manager (Hauptfunktion).
Liest das PDF mit PyMuPDF (schnell, gut bei Layouts).
Liest das PDF mit pdfplumber (langsam, gut bei Tabellen).
Sammelt alle Ergebnisse.
Deduplizierung & Logik: Entscheidet am Ende, was "Sicher" (beide Engines gefunden), "Unsicher" (nur eine Engine) oder "Spam" (zu häufig/falscher Kontext) ist.
Warum: Zwei Engines finden mehr als eine. Die Kombination macht das Tool robust.
Wann: Wird aufgerufen, wenn der User auf "Suche starten" klickt.
4. Exporter (
core/exporters.py
)
Kümmert sich um den Output.

export_to_excel(...)
Was: Nimmt die drei Ergebnis-Tabellen (Sicher, Unsicher, Spam) und schreibt sie in eine Excel-Datei.
Warum: Python kann Daten nicht einfach so "als Excel" ausspucken, man braucht einen speziellen Writer (xlsxwriter).
