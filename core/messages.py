from enum import Enum
from typing import Dict, Optional, Any


class MessageType(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class MessageCode(str, Enum):
    # Auth messages
    LOGIN_SUCCESS = "auth.login_success"
    LOGIN_FAILED = "auth.login_failed"
    REGISTER_SUCCESS = "auth.register_success"
    REGISTER_EMAIL_EXISTS = "auth.register_email_exists"
    REGISTRATION_FAILED = "auth.register_failed"
    PASSWORD_RESET_SUCCESS = "auth.password_reset_success"
    PASSWORD_RESET_FAILED = "auth.password_reset_failed"

    # Category messages
    CATEGORY_CREATED = "category.created"
    CATEGORY_UPDATED = "category.updated"
    CATEGORY_DELETED = "category.deleted"
    CATEGORY_DUPLICATE = "category.duplicate_name"

    # Expense messages
    EXPENSE_CREATED = "expense.created"
    EXPENSE_UPDATED = "expense.updated"
    EXPENSE_DELETED = "expense.deleted"

    # Profile messages
    PROFILE_UPDATED = "profile.updated"


# Message templates with placeholders
MESSAGE_TEMPLATES: Dict[MessageCode, str] = {
    MessageCode.LOGIN_SUCCESS: "Welcome back, {user_name}!",
    MessageCode.LOGIN_FAILED: "Invalid email or password",
    MessageCode.REGISTER_SUCCESS: "Account created successfully! Welcome to Bajeti, {first_name}!",
    MessageCode.REGISTER_EMAIL_EXISTS: "An account with this email already exists",
    MessageCode.REGISTRATION_FAILED: "Registration failed for email={email}",
    MessageCode.CATEGORY_CREATED: "Category '{category_name}' created successfully",
    MessageCode.CATEGORY_UPDATED: "Category '{category_name}' updated successfully",
    MessageCode.CATEGORY_DELETED: "Category deleted successfully",
    MessageCode.CATEGORY_DUPLICATE: "You already have a category named '{category_name}'",
    MessageCode.EXPENSE_CREATED: "Expense of {amount} added to {category_name}",
    MessageCode.EXPENSE_UPDATED: "Expense updated successfully",
    MessageCode.EXPENSE_DELETED: "Expense deleted successfully",
    MessageCode.PROFILE_UPDATED: "Profile updated successfully",
    MessageCode.PASSWORD_RESET_SUCCESS: "Password reset successfully! You can now login with your new password",
    MessageCode.PASSWORD_RESET_FAILED: "Unable to reset password. Please check your security answer",
}


def get_message(code: MessageCode, **kwargs) -> Dict[str, Any]:
    """Get formatted message with type and text"""
    template = MESSAGE_TEMPLATES.get(code, str(code))
    message_text = template.format(**kwargs)

    # Determine message from code
    if "success" in code.value:
        message_type = MessageType.SUCCESS
    elif "failed" in code.value or "error" in code.value:
        message_type = MessageType.ERROR
    elif "warning" in code.value:
        message_type = MessageType.WARNING
    else:
        message_type = MessageType.INFO

    return {
        "code": code.value,
        "text": message_text,
        "type": message_type
    }
