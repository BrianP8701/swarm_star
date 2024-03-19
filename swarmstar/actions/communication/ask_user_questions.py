"""
Throughout the conversation we maintain a "Conversation State" which is a data structure that contains the following:
    - A list of questions that need to be answered.
    - A concise and compact representation of only the necessary information to persist through the conversation.
    - A list of reports that is built up throughout the conversation. This report is what will be sent back when the conversation ends.
"""

from typing import List

from pydantic import BaseModel, Field

from swarmstar.models import BlockingOperation, TerminationOperation, UserCommunicationOperation
from swarmstar.abstract.base_action import BaseAction

class InitialQuestionAskerConversationState(BaseModel):
    questions: List[str] = Field(..., description="List of questions we need answered")
    persisted_context: str = Field(
        ...,
        description="A concise and compact representation of the necessary information to persist through the conversation.",
    )
    chat_name: str = Field(..., description="A 2-4 word name for the conversation")

class QuestionAskerConversationState(BaseModel):
    questions: List[str] = Field(..., description="List of questions we need answered")
    persisted_context: str = Field(
        ...,
        description="A concise and compact representation of the necessary information to persist through the conversation.",
    )
    report: str = Field(
        ...,
        description="Concise and comprehensive report of answers to our questions and supporting context.",
    )

GENERATE_INITIAL_CONVERSATION_STATE_INSTRUCTIONS = (
    "Steps:\n\n"
    "1. Identify the questions that need to be answered.\n"
    "2. Persist critical context that is needed for the conversation from the goal. This "
    "context should be minimal and directly support the agent in maintaining the conversation.\n"
    "3. Craft an initial message to the user that is concise and clear to avoid confusion.\n"
    "4. Create a 2-4 word name for the conversation.\n\n"
    "The reports aren't used as context throughout the conversation, so make sure all necessary context is in the persisted context."
).replace("\n", "\\n")

UPDATE_CONVERSATION_STATE_INSTRUCTIONS = (
    "Refine the conversation state based on the user's latest response.\n\n"
    "Steps:\n"
    "1. Update Questions: Rewrite the list of questions by removing resolved items and adding new ones as needed.\n"
    "2. Update Context: Rewrite the persisted context based off the most recent message. Keep it focused on essential "
    "information required for ongoing dialogue.\n"
    "3. Add to Reports: Add answers and relevant information to the reports given the users message. This report is what "
    "will be sent back when the conversation ends. Keep it brief and actionable yet comprehensive. What you say will be "
    "appended to the current reports so do not repeat stuff already mentioned.\n\n"
    "The reports aren't used as context throughout the conversation, so make sure all necessary context is in the persisted context."
).replace("\n", "\\n")

GENERATE_MESSAGE_INSTRUCTIONS = (
    "Generate a message to send to the user based on the current conversation state and the user's most recent message.\n"
    "You are given a list of questions that need to be answered. Don't stray off topic and aim to get answers to the questions."
).replace("\n", "\\n")

FINALIZE_REPORT_INSTRUCTIONS = (
    "Consolidate the list of reports into a final report."
).replace("\n", "\\n")


class Action(BaseAction):
    def main(self):
        return self.generate_initial_conversation_state()

    def generate_initial_conversation_state(self):
        system_message = (
            f"{GENERATE_INITIAL_CONVERSATION_STATE_INSTRUCTIONS}"
            f"You are initializing the conversation state. Extract questions and "
            f"context from this message:\n`{self.node.message}`"
        )
        messages = [
            {
                "role": "system",
                "content": system_message
            }
        ]
        
        self.log({
            "role": "swarmstar",
            "content": f"We want to get answers to these questions from the user: {self.node.message}\n\n"
        })
        self.log({
            "role": "system",
            "content": system_message
        })

        return BlockingOperation(
            node_id=self.node.id,
            blocking_type="instructor_completion",
            args={"messages": messages},
            context={
                "instructor_model_name": "InitialQuestionAskerConversationState"
            },
            next_function_to_call="handle_initial_conversation_state",
        )

    @BaseAction.receive_completion_handler
    def handle_initial_conversation_state(
        self,
        completion: InitialQuestionAskerConversationState,
    ):
        self.log({
            "role": "ai",
            "content": (
                f"Generated chat name: {completion.chat_name}\n\n"
                f"Questions: {completion.questions}\n\n"
                f"Persisted Context: {completion.persisted_context}\n\n"
            )
        })
        
        system_message = (
            f"{GENERATE_MESSAGE_INSTRUCTIONS}"
            f"Questions: {completion.questions}\n\n"
            f"Context: {completion.persisted_context}\n\n"
            f"Start the conversation off with a message that is clear and concise."
        )
        messages = [
            {"role": "system", "content": system_message}
        ]

        self.log({
            "role": "system",
            "content": system_message
        })
        
        return BlockingOperation(
            node_id=self.node.id,
            blocking_type="openai_completion",
            args={"messages": messages},
            context={
                "questions": completion.questions,
                "persisted_context": completion.persisted_context,
                "reports": [],
                "chat_name": completion.chat_name
            },
            next_function_to_call="send_user_first_message",
        )

    @BaseAction.receive_completion_handler
    def send_user_first_message(
        self,
        questions: List[str],
        persisted_context: str,
        reports: List[str],
        chat_name: str,
        completion: str,
    ):
        self.log({
            "role": "ai",
            "content": completion
        })
        
        return UserCommunicationOperation(
            node_id=self.node.id,
            message=completion,
            context={
                "questions": questions,
                "persisted_context": persisted_context,
                "reports": reports,
                "recent_ai_message": completion,
                "chat_name": chat_name,
            },
            next_function_to_call="update_conversation_state",
        )

    @BaseAction.receive_completion_handler
    def generate_message(
        self,
        user_message: str,
        recent_ai_message: str,
        reports: List[str],
        completion: QuestionAskerConversationState,
    ):
        self.log({
            "role": "ai",
            "content": (
                f"Questions: {completion.questions}\n\n"
                f"Persisted Context: {completion.persisted_context}\n\n"
                f"New Report: {completion.report}\n\n"
            )
        })
        
        system_message = (
            f"{GENERATE_MESSAGE_INSTRUCTIONS}"
            f"Questions: {completion.questions}\n\n"
            f"Context: {completion.persisted_context}\n\n"
            f"User's most recent message: {user_message}\n"
            f"Your most recent message: {recent_ai_message}"
        )
        messages = [
            {"role": "system", "content": system_message}
        ]

        self.log({
            "role": "system",
            "content": system_message
        })
        
        return BlockingOperation(
            node_id=self.node.id,
            blocking_type="openai_completion",
            args={"messages": messages},
            context={
                "questions": completion.questions,
                "persisted_context": completion.persisted_context,
                "reports": reports
            },
            next_function_to_call="send_user_message",
        )

    @BaseAction.receive_completion_handler
    def send_user_message(
        self,
        questions: List[str],
        persisted_context: str,
        reports: List[str],
        completion: str,
    ):
        self.log({
            "role": "ai",
            "content": completion
        })
        
        return UserCommunicationOperation(
            node_id=self.node.id,
            message=completion,
            context={
                "questions": questions,
                "persisted_context": persisted_context,
                "reports": reports,
                "recent_ai_message": completion,
            },
            next_function_to_call="update_conversation_state",
        )

    def update_conversation_state(
        self,
        questions: List[str],
        persisted_context: str,
        reports: List[str],
        recent_ai_message: str,
        user_response: str,
    ):
        self.log({
            "role": "user",
            "content": user_response
        })
        
        system_message = (
            f"{UPDATE_CONVERSATION_STATE_INSTRUCTIONS}"
            f"Update Questions: {questions}\n\n"
            f"Update Context: {persisted_context}\n\n"
            f"Add to Reports: {reports}\n\n"
            f"Your (you, the ais) most recent message: {recent_ai_message}"
        )
        messages = [
            {"role": "system", "content": system_message},
            {
                "role": "user",
                "content": user_response
            }
        ]

        self.log({
            "role": "system",
            "content": system_message
        })
        
        return BlockingOperation(
            node_id=self.node.id,
            blocking_type="instructor_completion",
            args={
                "messages": messages
            },
            context={
                "reports": reports,
                "user_response": user_response,
                "recent_ai_message": recent_ai_message,
                "instructor_model_name": "QuestionAskerConversationState"
            },
            next_function_to_call="decide_to_continue_or_end_conversation",
        )

    @BaseAction.receive_completion_handler
    def decide_to_continue_or_end_conversation(
        self,
        reports: List[str],
        user_response: str,
        recent_ai_message: str,
        completion: QuestionAskerConversationState,
    ):
        reports.append(completion.report)
        if (not completion.questions) or (len(completion.questions) == 0):
            self.log({
                "role": "ai",
                "content": (
                    f"Questions: {completion.questions}\n\n"
                    f"Persisted Context: {completion.persisted_context}\n\n"
                    f"New Report: {completion.report}\n\n"
                )
            })
            return self.finalize_report(reports)

        return self.generate_message(
            user_response, recent_ai_message, reports, completion
        )

    def finalize_report(self, reports: List[str]):
        self.log({
            "role": "swarmstar",
            "content": f"Finalizing the report."
        })
        system_message = FINALIZE_REPORT_INSTRUCTIONS + f"\n\nReports: {reports}"
        messages = [{"role": "system", "content": system_message}]
        
        self.log({
            "role": "system",
            "content": system_message
        })

        return BlockingOperation(
            node_id=self.node.id,
            blocking_type="openai_completion",
            args={"messages": messages},
            context={},
            next_function_to_call="terminate_conversation",
        )

    @BaseAction.receive_completion_handler
    def terminate_conversation(self, completion: str):
        self.log({
            "role": "ai",
            "content": completion
        })
        self.report(
            "The agent created a final report after having a conversation with the user "
            f"with the intent of answering a given set of questions.\n\nQuestions: {self.node.message}"
            f"\n\nReport: {completion}"
        )
        return TerminationOperation(
            node_id=self.node.id,
            terminator_node_id=self.node.id,
        )
