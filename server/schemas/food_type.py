"""
Food Type Schemas for Wedding Food Menu System
Path: server/schemas/food_type.py
"""
from pydantic import BaseModel, Field
from typing import List, Optional


# server/schemas/food.py
from pydantic import BaseModel
from typing import List


# class FoodMenuOut(BaseModel):
#     id: int
#     food_type: str
#     number_of_visitors: int
#     menu_details: str

#     class Config:
#         from_attributes  = True


class FoodMenuOut(BaseModel):
    id: int
    food_type: str
    number_of_visitors: int
    menu_details: list[str]  # Expect a list, not a string

    class Config:
        from_attributes = True


class FoodTypeBase(BaseModel):
    """Base schema for food type"""
    name: str = Field(...,
                      description="Type of food (e.g., Traditional, Modern, Mixed)")
    clan_id: int = Field(...,
                         description="ID of the clan this food type belongs to")


class FoodTypeCreate(FoodTypeBase):
    """Schema for creating a new food type"""
    pass


class FoodTypeUpdate(FoodTypeBase):
    """Schema for updating an existing food type"""
    id: int = Field(..., description="ID of the food type to update")


class FoodTypeResponse(FoodTypeBase):
    """Schema for food type response"""
    id: int = Field(..., description="ID of the food type")

    class Config:
        from_attributes = True
        from_attributes = True


class FoodTypeListResponse(BaseModel):
    """Schema for listing food types"""
    id: int
    name: str
    clan_id: int

    class Config:
        from_attributes = True
        from_attributes = True


class FoodTypeDropdownResponse(BaseModel):
    """Schema for food type dropdown options"""
    food_types: List[FoodTypeResponse]

    class Config:
        from_attributes = True
        from_attributes = True


class FoodTypeOption(BaseModel):
    """Schema for food type dropdown options"""
    value: str
    label: str


class VisitorOption(BaseModel):
    """Schema for visitor count dropdown options"""
    value: int
    label: str


class MenuResponse(BaseModel):
    """Schema for menu response to grooms"""
    food_type_id: int
    visitors: int
    menu_items: List[str]


class Menuget(BaseModel):
    """Schema for menu response to grooms"""
    food_type: str
    visitors: int


class CreateFoodMenuRequest(BaseModel):
    """Schema for creating new food menus"""
    food_type: str = Field(..., description="Traditional, Modern, or Mixed")
    number_of_visitors: int = Field(...,
                                    description="Number of visitors (100-500)")
    menu_items: List[str] = Field(..., description="List of menu items")
    clan_id: int = Field(..., description="Clan ID")

    # class Config:
    #     schema_extra = {
    #         "example": {
    #             "food_type": "Traditional",
    #             "number_of_visitors": 200,
    #             "menu_items": [
    #                 "40kg بطاطس (Potatoes)",
    #                 "30kg طماطم (Tomatoes)",
    #                 "20kg بصل (Onions)",
    #                 "50kg أرز (Rice)",
    #                 "60kg لحم خروف (Lamb Meat)"
    #             ],
    #             "clan_id": 1
    #         }
    #     }


class UpdateFoodMenuRequest(BaseModel):
    """Schema for updating existing food menus"""
    menu_items: List[str] = Field(...,
                                  description="Updated list of menu items")
    food_type: Optional[str] = Field(
        None, description="Updated food type (optional)")
    number_of_visitors: Optional[int] = Field(
        None, description="Updated number of visitors (optional)")

    # class Config:
    #     schema_extra = {
    #         "example": {
    #             "menu_items": [
    #                 "45kg بطاطس (Potatoes)",
    #                 "35kg طماطم (Tomatoes)",
    #                 "25kg بصل (Onions)",
    #                 "55kg أرز (Rice)",
    #                 "65kg لحم خروف (Lamb Meat)"
    #             ],
    #             "food_type": "Traditional",
    #             "number_of_visitors": 220
    #         }
    #     }


class FoodMenuListResponse(BaseModel):
    """Schema for listing food menus"""
    id: int
    food_type: str
    number_of_visitors: int
    clan_id: int

    class Config:
        from_attributes = True


class FoodMenuDetailResponse(BaseModel):
    """Schema for detailed food menu information"""
    id: int
    food_type: str
    number_of_visitors: int
    menu_items: List[str]
    clan_id: int

    class Config:
        from_attributes = True
