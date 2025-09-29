
import json
from server.models.food import FoodMenu


def create_default_food_menus(db, clan_id: int):
    """
    Create default food menus for the default clan
    """
    sample_menus = [
        # Traditional Food Menus
        {
            "food_type": "Traditional",
            "visitors": 100,
            "items": [
                "20kg بطاطس (Potatoes)",
                "15kg طماطم (Tomatoes)",
                "10kg بصل (Onions)",
                "25kg أرز (Rice)",
                "30kg لحم خروف (Lamb Meat)",
                "12kg خضار مشكلة (Mixed Vegetables)",
                "200 قطعة خبز تقليدي (Traditional Bread)",
                "8 لتر زيت طبخ (Cooking Oil)",
                "2kg بهارات تقليدية (Traditional Spices)"
            ]
        },
        {
            "food_type": "Traditional",
            "visitors": 150,
            "items": [
                "30kg بطاطس (Potatoes)",
                "22kg طماطم (Tomatoes)",
                "15kg بصل (Onions)",
                "37kg أرز (Rice)",
                "45kg لحم خروف (Lamb Meat)",
                "18kg خضار مشكلة (Mixed Vegetables)",
                "300 قطعة خبز تقليدي (Traditional Bread)",
                "12 لتر زيت طبخ (Cooking Oil)",
                "3kg بهارات تقليدية (Traditional Spices)"
            ]
        },
        {
            "food_type": "Traditional",
            "visitors": 200,
            "items": [
                "40kg بطاطس (Potatoes)",
                "30kg طماطم (Tomatoes)",
                "20kg بصل (Onions)",
                "50kg أرز (Rice)",
                "60kg لحم خروف (Lamb Meat)",
                "24kg خضار مشكلة (Mixed Vegetables)",
                "400 قطعة خبز تقليدي (Traditional Bread)",
                "16 لتر زيت طبخ (Cooking Oil)",
                "4kg بهارات تقليدية (Traditional Spices)"
            ]
        },
        {
            "food_type": "Traditional",
            "visitors": 250,
            "items": [
                "50kg بطاطس (Potatoes)",
                "37kg طماطم (Tomatoes)",
                "25kg بصل (Onions)",
                "62kg أرز (Rice)",
                "75kg لحم خروف (Lamb Meat)",
                "30kg خضار مشكلة (Mixed Vegetables)",
                "500 قطعة خبز تقليدي (Traditional Bread)",
                "20 لتر زيت طبخ (Cooking Oil)",
                "5kg بهارات تقليدية (Traditional Spices)"
            ]
        },
        {
            "food_type": "Traditional",
            "visitors": 300,
            "items": [
                "60kg بطاطس (Potatoes)",
                "45kg طماطم (Tomatoes)",
                "30kg بصل (Onions)",
                "75kg أرز (Rice)",
                "90kg لحم خروف (Lamb Meat)",
                "36kg خضار مشكلة (Mixed Vegetables)",
                "600 قطعة خبز تقليدي (Traditional Bread)",
                "24 لتر زيت طبخ (Cooking Oil)",
                "6kg بهارات تقليدية (Traditional Spices)"
            ]
        },
        {
            "food_type": "Traditional",
            "visitors": 400,
            "items": [
                "80kg بطاطس (Potatoes)",
                "60kg طماطم (Tomatoes)",
                "40kg بصل (Onions)",
                "100kg أرز (Rice)",
                "120kg لحم خروف (Lamb Meat)",
                "48kg خضار مشكلة (Mixed Vegetables)",
                "800 قطعة خبز تقليدي (Traditional Bread)",
                "32 لتر زيت طبخ (Cooking Oil)",
                "8kg بهارات تقليدية (Traditional Spices)"
            ]
        },
        {
            "food_type": "Traditional",
            "visitors": 500,
            "items": [
                "100kg بطاطس (Potatoes)",
                "75kg طماطم (Tomatoes)",
                "50kg بصل (Onions)",
                "125kg أرز (Rice)",
                "150kg لحم خروف (Lamb Meat)",
                "60kg خضار مشكلة (Mixed Vegetables)",
                "1000 قطعة خبز تقليدي (Traditional Bread)",
                "40 لتر زيت طبخ (Cooking Oil)",
                "10kg بهارات تقليدية (Traditional Spices)"
            ]
        },

        # Modern Food Menus
        {
            "food_type": "Modern",
            "visitors": 100,
            "items": [
                "15kg بطاطس (Potatoes)",
                "10kg طماطم (Tomatoes)",
                "8kg بصل (Onions)",
                "20kg أرز (Rice)",
                "35kg دجاج (Chicken)",
                "18kg خضار طازجة (Fresh Vegetables)",
                "150 قطعة خبز حديث (Dinner Rolls)",
                "6 لتر زيت زيتون (Olive Oil)",
                "1.5kg بهارات عالمية (International Spices)",
                "5kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Modern",
            "visitors": 150,
            "items": [
                "22kg بطاطس (Potatoes)",
                "15kg طماطم (Tomatoes)",
                "12kg بصل (Onions)",
                "30kg أرز (Rice)",
                "52kg دجاج (Chicken)",
                "27kg خضار طازجة (Fresh Vegetables)",
                "225 قطعة خبز حديث (Dinner Rolls)",
                "9 لتر زيت زيتون (Olive Oil)",
                "2.25kg بهارات عالمية (International Spices)",
                "7.5kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Modern",
            "visitors": 200,
            "items": [
                "30kg بطاطس (Potatoes)",
                "20kg طماطم (Tomatoes)",
                "16kg بصل (Onions)",
                "40kg أرز (Rice)",
                "70kg دجاج (Chicken)",
                "36kg خضار طازجة (Fresh Vegetables)",
                "300 قطعة خبز حديث (Dinner Rolls)",
                "12 لتر زيت زيتون (Olive Oil)",
                "3kg بهارات عالمية (International Spices)",
                "10kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Modern",
            "visitors": 250,
            "items": [
                "37kg بطاطس (Potatoes)",
                "25kg طماطم (Tomatoes)",
                "20kg بصل (Onions)",
                "50kg أرز (Rice)",
                "87kg دجاج (Chicken)",
                "45kg خضار طازجة (Fresh Vegetables)",
                "375 قطعة خبز حديث (Dinner Rolls)",
                "15 لتر زيت زيتون (Olive Oil)",
                "3.75kg بهارات عالمية (International Spices)",
                "12.5kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Modern",
            "visitors": 300,
            "items": [
                "45kg بطاطس (Potatoes)",
                "30kg طماطم (Tomatoes)",
                "24kg بصل (Onions)",
                "60kg أرز (Rice)",
                "105kg دجاج (Chicken)",
                "54kg خضار طازجة (Fresh Vegetables)",
                "450 قطعة خبز حديث (Dinner Rolls)",
                "18 لتر زيت زيتون (Olive Oil)",
                "4.5kg بهارات عالمية (International Spices)",
                "15kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Modern",
            "visitors": 400,
            "items": [
                "60kg بطاطس (Potatoes)",
                "40kg طماطم (Tomatoes)",
                "32kg بصل (Onions)",
                "80kg أرز (Rice)",
                "140kg دجاج (Chicken)",
                "72kg خضار طازجة (Fresh Vegetables)",
                "600 قطعة خبز حديث (Dinner Rolls)",
                "24 لتر زيت زيتون (Olive Oil)",
                "6kg بهارات عالمية (International Spices)",
                "20kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Modern",
            "visitors": 500,
            "items": [
                "75kg بطاطس (Potatoes)",
                "50kg طماطم (Tomatoes)",
                "40kg بصل (Onions)",
                "100kg أرز (Rice)",
                "175kg دجاج (Chicken)",
                "90kg خضار طازجة (Fresh Vegetables)",
                "750 قطعة خبز حديث (Dinner Rolls)",
                "30 لتر زيت زيتون (Olive Oil)",
                "7.5kg بهارات عالمية (International Spices)",
                "25kg معكرونة (Pasta)"
            ]
        },

        # Mixed Food Menus
        {
            "food_type": "Mixed",
            "visitors": 100,
            "items": [
                "25kg بطاطس (Potatoes)",
                "18kg طماطم (Tomatoes)",
                "12kg بصل (Onions)",
                "30kg أرز (Rice)",
                "20kg لحم خروف (Lamb Meat)",
                "15kg دجاج (Chicken)",
                "20kg خضار مشكلة (Mixed Vegetables)",
                "250 قطعة خبز مشكل (Mixed Bread)",
                "10 لتر زيت طبخ (Cooking Oil)",
                "2.5kg بهارات مشكلة (Mixed Spices)",
                "3kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Mixed",
            "visitors": 150,
            "items": [
                "37kg بطاطس (Potatoes)",
                "27kg طماطم (Tomatoes)",
                "18kg بصل (Onions)",
                "45kg أرز (Rice)",
                "30kg لحم خروف (Lamb Meat)",
                "22kg دجاج (Chicken)",
                "30kg خضار مشكلة (Mixed Vegetables)",
                "375 قطعة خبز مشكل (Mixed Bread)",
                "15 لتر زيت طبخ (Cooking Oil)",
                "3.75kg بهارات مشكلة (Mixed Spices)",
                "4.5kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Mixed",
            "visitors": 200,
            "items": [
                "50kg بطاطس (Potatoes)",
                "36kg طماطم (Tomatoes)",
                "24kg بصل (Onions)",
                "60kg أرز (Rice)",
                "40kg لحم خروف (Lamb Meat)",
                "30kg دجاج (Chicken)",
                "40kg خضار مشكلة (Mixed Vegetables)",
                "500 قطعة خبز مشكل (Mixed Bread)",
                "20 لتر زيت طبخ (Cooking Oil)",
                "5kg بهارات مشكلة (Mixed Spices)",
                "6kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Mixed",
            "visitors": 250,
            "items": [
                "62kg بطاطس (Potatoes)",
                "45kg طماطم (Tomatoes)",
                "30kg بصل (Onions)",
                "75kg أرز (Rice)",
                "50kg لحم خروف (Lamb Meat)",
                "37kg دجاج (Chicken)",
                "50kg خضار مشكلة (Mixed Vegetables)",
                "625 قطعة خبز مشكل (Mixed Bread)",
                "25 لتر زيت طبخ (Cooking Oil)",
                "6.25kg بهارات مشكلة (Mixed Spices)",
                "7.5kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Mixed",
            "visitors": 300,
            "items": [
                "75kg بطاطس (Potatoes)",
                "54kg طماطم (Tomatoes)",
                "36kg بصل (Onions)",
                "90kg أرز (Rice)",
                "60kg لحم خروف (Lamb Meat)",
                "45kg دجاج (Chicken)",
                "60kg خضار مشكلة (Mixed Vegetables)",
                "750 قطعة خبز مشكل (Mixed Bread)",
                "30 لتر زيت طبخ (Cooking Oil)",
                "7.5kg بهارات مشكلة (Mixed Spices)",
                "9kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Mixed",
            "visitors": 400,
            "items": [
                "100kg بطاطس (Potatoes)",
                "72kg طماطم (Tomatoes)",
                "48kg بصل (Onions)",
                "120kg أرز (Rice)",
                "80kg لحم خروف (Lamb Meat)",
                "60kg دجاج (Chicken)",
                "80kg خضار مشكلة (Mixed Vegetables)",
                "1000 قطعة خبز مشكل (Mixed Bread)",
                "40 لتر زيت طبخ (Cooking Oil)",
                "10kg بهارات مشكلة (Mixed Spices)",
                "12kg معكرونة (Pasta)"
            ]
        },
        {
            "food_type": "Mixed",
            "visitors": 500,
            "items": [
                "125kg بطاطس (Potatoes)",
                "90kg طماطم (Tomatoes)",
                "60kg بصل (Onions)",
                "150kg أرز (Rice)",
                "100kg لحم خروف (Lamb Meat)",
                "75kg دجاج (Chicken)",
                "100kg خضار مشكلة (Mixed Vegetables)",
                "1250 قطعة خبز مشكل (Mixed Bread)",
                "50 لتر زيت طبخ (Cooking Oil)",
                "12.5kg بهارات مشكلة (Mixed Spices)",
                "15kg معكرونة (Pasta)"
            ]
        }
    ]

    # Insert all sample menus
    for menu_data in sample_menus:
        # Check if menu already exists
        existing = db.query(FoodMenu).filter(
            FoodMenu.food_type == menu_data["food_type"],
            FoodMenu.number_of_visitors == menu_data["visitors"],
            FoodMenu.clan_id == clan_id
        ).first()

        if not existing:
            menu = FoodMenu(
                food_type=menu_data["food_type"],
                number_of_visitors=menu_data["visitors"],
                menu_details=json.dumps(menu_data["items"]),
                clan_id=clan_id
            )
            db.add(menu)

    db.commit()
    print(f"Default food menus created for clan {clan_id}!")
