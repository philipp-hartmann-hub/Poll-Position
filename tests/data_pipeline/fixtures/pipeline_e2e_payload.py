"""Reichhaltiges Dawum-Fixture für den Offline-Pipeline-E2E-Test (keine Live-API)."""

from __future__ import annotations

# Bewusst als Python-Modul: leicht erweiterbar, kein zweites JSON pflegen.
# Anteile ≈ 100 %, mehrere Surveys für Gold-Trends.

PAYLOAD: dict = {
    "Database": {
        "License": {
            "Name": "ODC Open Database License",
            "Shortcut": "ODC-ODbL",
            "Link": "https://opendatacommons.org/licenses/odbl/1-0/",
        },
        "Publisher": "dawum.de",
        "Author": "Dipl.-Jur. Philipp Guttmann",
        "Last_Update": "2026-08-01T12:00:00+02:00",
    },
    "Parliaments": {
        "0": {
            "Shortcut": "Bundestag",
            "Name": "Bundestag",
            "Election": "Bundestagswahl",
        }
    },
    "Institutes": {
        "5": {"Name": "INSA"},
        "2": {"Name": "Forsa"},
    },
    "Taskers": {
        "3": {"Name": "BILD am Sonntag"},
        "1": {"Name": "RTL/n-tv"},
    },
    "Methods": {
        "4": {"Name": "Telefon & Online"},
        "3": {"Name": "Online"},
    },
    "Parties": {
        "0": {"Shortcut": "Sonstige", "Name": "sonstige Parteien"},
        "1": {
            "Shortcut": "CDU/CSU",
            "Name": "Christlich Demokratische Union / Christlich-Soziale Union",
        },
        "2": {"Shortcut": "SPD", "Name": "Sozialdemokratische Partei Deutschlands"},
        "3": {"Shortcut": "FDP", "Name": "Freie Demokratische Partei"},
        "4": {"Shortcut": "Grüne", "Name": "Bündnis 90/Die Grünen"},
        "5": {"Shortcut": "Linke", "Name": "Die Linke"},
        "7": {"Shortcut": "AfD", "Name": "Alternative für Deutschland"},
        "23": {"Shortcut": "BSW", "Name": "Bündnis Sahra Wagenknecht"},
    },
    "Surveys": {
        "9001": {
            "Date": "2026-07-20",
            "Survey_Period": {"Date_Start": "2026-07-15", "Date_End": "2026-07-18"},
            "Surveyed_Persons": "1500",
            "Parliament_ID": "0",
            "Institute_ID": "5",
            "Tasker_ID": "3",
            "Method_ID": "4",
            "Results": {
                "1": 27.0,
                "7": 25.0,
                "2": 15.0,
                "4": 12.0,
                "5": 8.0,
                "23": 4.0,
                "3": 4.0,
                "0": 5.0,
            },
        },
        "9002": {
            "Date": "2026-07-28",
            "Survey_Period": {"Date_Start": "2026-07-22", "Date_End": "2026-07-26"},
            "Surveyed_Persons": "2000",
            "Parliament_ID": "0",
            "Institute_ID": "2",
            "Tasker_ID": "1",
            "Method_ID": "3",
            "Results": {
                "1": 26.0,
                "7": 26.0,
                "2": 14.0,
                "4": 13.0,
                "5": 9.0,
                "23": 3.0,
                "3": 4.0,
                "0": 5.0,
            },
        },
    },
}
