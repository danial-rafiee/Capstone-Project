# Coach panel data structure

class CoachPanel:

    def __init__(self, question: str = "", answer: str = "", status: str = ""):
        self.configure(question, answer, status)

    def configure(self, question: str = "", answer: str = "", status: str = "") -> None:
        question = self._text(question)
        answer = self._text(answer)
        status = self._text(status) if status is not None else ""
        self._question, self._answer, self._status = question, answer, status

    @staticmethod
    def _text(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("Panel values must be text.")
        return value.strip()

    def get_question(self) -> str:
        return self._question

    def set_question(self, value: str) -> None:
        self.configure(value, self._answer, self._status)

    def get_answer(self) -> str:
        return self._answer

    def set_answer(self, value: str) -> None:
        self.configure(self._question, value, self._status)

    def get_status(self) -> str:
        return self._status

    def set_status(self, value: str) -> None:
        self.configure(self._question, self._answer, value)

    question = property(get_question, set_question)
    answer = property(get_answer, set_answer)
    status = property(get_status, set_status)

    def submit_question(self, question: str) -> None:
        question = self._text(question)
        if not question:
            raise ValueError("Submitted question must not be empty.")
        # A previous answer must not appear as the answer to a different question.
        self.configure(question, "", "")

    def set_response(self, answer: str, status: str = "") -> None:
        self.configure(self._question, answer, status)

    def to_dict(self) -> dict:
        data = {"question": self._question, "answer": self._answer}
        if self._status:
            data["status"] = self._status
        return data

    def __str__(self) -> str:
        return f"CoachPanel(status='{self._status}', question='{self._question[:30]}...')"