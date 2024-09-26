import streamlit as st
from streamlit_feedback import streamlit_feedback


class FeedbackManager:
    def __init__(self, feedback_type="thumbs", optional_text_label="Por favor nos dê seu feedback!"):
        self.feedback_type = feedback_type
        self.optional_text_label = optional_text_label
        self.feedback = None

    def _submit_feedback(self, user_response, emoji=None):
        st.toast(f"Feedback enviado: {user_response}", icon=emoji)
        return user_response.update({"some metadata": 123})

    def get_feedback(self):
        feedback = streamlit_feedback(
            feedback_type=self.feedback_type,
            optional_text_label=self.optional_text_label,
            on_submit=self._submit_feedback
        )

        if feedback:
            st.write(":orange[Feedback recebido:]")
            st.write(feedback)
            self.feedback = feedback
        return feedback
