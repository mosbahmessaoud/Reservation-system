# """
# Script to populate sample food menu data
# Path: server/scripts/setup_food_data.py

# Run this script once to populate your database with sample food menus
# """

# from sqlalchemy.orm import Session
# from ..db import get_db, engine
# from ..routes.food_route import create_sample_menus


# def setup_food_data_for_all_clans():
#     """Setup sample food data for all existing clans"""

#     # Create database session
#     db = Session(bind=engine)

#     try:
#         # Get all clan IDs from your clans table
#         clan_ids = db.execute("SELECT id FROM clans").fetchall()

#         for (clan_id,) in clan_ids:
#             print(f"Creating sample food menus for clan {clan_id}...")
#             create_sample_menus(db, clan_id)

#         print("✅ Sample food data created successfully for all clans!")

#     except Exception as e:
#         print(f"❌ Error creating sample data: {e}")
#         db.rollback()
#     finally:
#         db.close()


# def setup_food_data_for_specific_clan(clan_id: int):
#     """Setup sample food data for a specific clan"""

#     db = Session(bind=engine)

#     try:
#         print(f"Creating sample food menus for clan {clan_id}...")
#         create_sample_menus(db, clan_id)
#         print(f"✅ Sample food data created successfully for clan {clan_id}!")

#     except Exception as e:
#         print(f"❌ Error creating sample data: {e}")
#         db.rollback()
#     finally:
#         db.close()


# if __name__ == "__main__":
#     # Option 1: Setup for all clans
#     setup_food_data_for_all_clans()

#     # Option 2: Setup for specific clan (uncomment and change clan_id)
#     # setup_food_data_for_specific_clan(1)
