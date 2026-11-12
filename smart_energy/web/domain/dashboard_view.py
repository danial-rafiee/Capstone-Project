# Dashboard view handler for Subsystem A

class DashboardView:
    def __init__(self, building_id: int = 1):
        self.building_id = building_id

    def handle_request(self, request_args: dict) -> dict:
        preset = request_args.get('preset', '24h')
        question = request_args.get('question', '').strip()

        # Fallback to default question if the submitted question is empty
        if not question:
            question = "How can we optimize energy consumption during off-hours without violating essential loads?"

        return {"preset": preset, "question": question}