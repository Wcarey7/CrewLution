def set_active_company(*, request, company_id):
  membership = request.user.company_memberships.filter(
    company_id=company_id,
    is_active=True,
  ).select_related("company").first()

  if not membership:
    raise ValueError("You do not belong to that company.")

  request.session["active_company_id"] = str(company_id)
  return membership