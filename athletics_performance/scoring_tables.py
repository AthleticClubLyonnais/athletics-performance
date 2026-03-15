class ScoringTables:
    """
    A class to calculate scores based on performance using World Athletics scoring tables.
    """

    def __init__(self, tables):
        """
        Initialize the ScoringTables class.

        :param tables: A dictionary containing event names as keys and their scoring parameters as values.
        """
        self.tables = tables

    def calculate_score(self, event, performance):
        """
        Calculate the score for a given event and performance.

        :param event: The name of the event.
        :param performance: The performance value (e.g., time, distance, height).
        :return: The calculated score.
        :raises ValueError: If the event is not found in the scoring tables.
        """
        if event not in self.tables:
            raise ValueError(f"Event '{event}' not found in scoring tables.")

        a, b, c = self.tables[event]
        score = a * (abs(performance - b) ** c)
        return int(score)

    def get_performance(self, event, score):
        """
        Calculate the performance for a given event and score.

        :param event: The name of the event.
        :param score: The score value.
        :return: The calculated performance.
        :raises ValueError: If the event is not found in the scoring tables.
        """
        if event not in self.tables:
            raise ValueError(f"Event '{event}' not found in scoring tables.")

        a, b, c = self.tables[event]
        performance = b + ((score / a) ** (1 / c))
        return performance