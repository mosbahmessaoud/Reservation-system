# """
# FastAPI app entry point. Includes all routers, creates tables, and seeds initial data.
# """

# import os
# from datetime import datetime
# from fastapi import FastAPI
# from dotenv import load_dotenv
# import json

# from server.auth_utils import get_password_hash
# from server.routes import food_route
# from server.scripts.food_initial_data import create_default_food_menus

# from server.routes.auth import router
# from server.routes.clan_admin import router
# from .db import engine, Base, SessionLocal
# # Import ALL models FIRST before any database operations
# from .models.user import User, UserRole
# from .models.county import County
# from .models.clan import Clan
# from .models.hall import Hall
# from .models.clan_settings import ClanSettings
# from .models.clan_rules import ClanRules  # Make sure this is imported!
# from .models.food import FoodMenu
# from .models.committee import HaiaCommittee, MadaehCommittee
# from .models.reservation import Reservation, ReservationStatus

# from .routes import auth, super_admin, clan_admin, reservations, grooms, food_route, public_routes
# # In your main.py or app setup

# # ✅ Load .env file
# load_dotenv()

# # ✅ Optional debug print to confirm env vars are loading
# print("TWILIO_ACCOUNT_SID:", os.getenv("TWILIO_ACCOUNT_SID"))
# print("TWILIO_PHONE_NUMBER:", os.getenv("TWILIO_PHONE_NUMBER"))

# # Initialize FastAPI app
# app = FastAPI(title="Wedding Reservation API")

# # ✅ Register routers
# app.include_router(auth.router)
# app.include_router(super_admin.router)
# app.include_router(clan_admin.router)
# app.include_router(reservations.router)
# app.include_router(grooms.router)
# app.include_router(food_route.router)
# app.include_router(public_routes.router)


# # Drop all tables (dangerous in production!)
# # Base.metadata.drop_all(bind=engine)

# # ✅ Create tables (safe in dev, be careful in prod)
# Base.metadata.create_all(bind=engine)


# # ✅ Initial seed data for first-time use
# def seed_initial_data():
#     db = SessionLocal()

#     if db.query(User).count() == 0:
#         # Create County
#         county = County(name="تغردايت")
#         db.add(county)
#         db.commit()
#         db.refresh(county)

#         # Create Clan
#         clan = Clan(name="عشيرة ات الحاج", county_id=county.id)
#         db.add(clan)
#         db.commit()
#         db.refresh(clan)

#         # Create Clan Settings
#         settings = ClanSettings(clan_id=clan.id)
#         db.add(settings)
#         db.commit()

#         # Create Hall
#         hall = Hall(name="دار " + clan.name, capacity=500, clan_id=clan.id)
#         db.add(hall)
#         db.commit()

#         # Super Admin
#         super_admin = User(
#             phone_number="0658890501",
#             password_hash=get_password_hash("M.superadmin"),
#             role=UserRole.super_admin,
#             first_name="Super",
#             last_name="Admin",
#             father_name="Root",
#             grandfather_name="Root",
#         )
#         db.add(super_admin)

#         db.commit()
#         print("✅ Initial data seeded successfully!")

#     db.close()


# # Seed data when app starts
# seed_initial_data()

