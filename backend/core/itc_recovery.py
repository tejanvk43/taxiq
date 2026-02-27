from typing import Any, Dict, List


class ITCRecoveryPipeline:
    """
    Kanban-style recovery pipeline scaffold.
    """

    async def get_pipeline(self, gstin: str, period: str) -> Dict[str, Any]:
        _ = period
        return {
            "gstin": gstin,
            "columns": [
                {
                    "id": "IDENTIFIED",
                    "title": "Identified",
                    "cards": [
                        {"id": "REC-001", "vendor": "GoldStar Traders", "amount": 99900, "action": "Generate Notice"},
                        {"id": "REC-002", "vendor": "Shadow Supplies", "amount": 118000, "action": "Follow-up / GSTR-1 filing"},
                    ],
                },
                {
                    "id": "NOTICE_SENT",
                    "title": "Notice Sent",
                    "cards": [{"id": "REC-003", "vendor": "Falcon Components", "amount": 44250, "action": "Await response"}],
                },
                {"id": "RECOVERED", "title": "Recovered", "cards": [{"id": "REC-004", "vendor": "Zenith Metals", "amount": 65000}]},
            ],
        }
