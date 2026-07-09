from django.contrib.auth import get_user_model
from django.db import transaction
from accounts.models import Company, CompanyMembership


User = get_user_model()

@transaction.atomic
def register_owner(*, email: str, password: str, company_name: str):
    """
    Registers a new company and creates an owner user for that company.

    Args:
        email (str): The email address of the owner user.
        password (str): The password for the owner user.
        company_name (str): The name of the company to be created.

    Returns:
        tuple: A tuple containing the newly created User, Company, and CompanyMembership instances.
    """

    username = email.lower()

    if User.objects.filter(username__iexact=username).exists():
        raise ValueError("An account with this email already exists.")

    if User.objects.filter(email__iexact=email).exists():
        raise ValueError("An account with this email already exists.")

    # Create the owner user
    user = User.objects.create_user(username=username, email=email.lower(), password=password)

    # Create the company
    company = Company.objects.create(name=company_name)

    # Create a membership for the owner user with the role of 'owner'
    membership = CompanyMembership.objects.create(
        company=company,
        user=user,
        role=CompanyMembership.Role.OWNER
        )

    return user, company, membership