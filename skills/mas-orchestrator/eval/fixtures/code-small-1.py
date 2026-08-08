def display_name(user):
    parts = [user.first_name, user.last_name]
    return " ".join(p.strip() for p in parts if p)
