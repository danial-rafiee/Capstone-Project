# Coach panel data structure

class CoachPanel:

    def __init__(self, question: str = "", answer: str = ""):
        self.configure(question, answer)

    def configure(self, question: str = "", answer: str = "") -> None:
        question = self._text(question)
        answer = self._text(answer)
        self._question, self._answer = question, answer

    @staticmethod
    def _text(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("Panel values must be text.")
        return value.strip()

    def get_question(self) -> str:
        return self._question

    def set_question(self, value: str) -> None:
        self.configure(value, self._answer)

    def get_answer(self) -> str:
        return self._answer

    def set_answer(self, value: str) -> None:
        self.configure(self._question, value)

    question = property(get_question, set_question)
    answer = property(get_answer, set_answer)

    def submit_question(self, question: str) -> None:
        question = self._text(question)
        if not question:
            raise ValueError("Submitted question must not be empty.")
        # A previous answer must not appear as the answer to a different question.
        self.configure(question, "")

    def set_response(self, answer: str) -> None:
        self.set_answer(answer)

    def to_dict(self) -> dict:
        return {"question": self._question, "answer": self._answer}
