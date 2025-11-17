"""
Food Routes for Wedding Food Menu System
Path: server/routes/food_route.py
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from server.models.clan import Clan

from ..models.food import FoodMenu
from ..auth_utils import get_current_user, require_role
from ..models.user import User, UserRole

from ..db import get_db
from ..schemas.food_type import (
    FoodMenuOut,
    FoodTypeListResponse,
    Menuget,
    VisitorOption,
    MenuResponse,
    CreateFoodMenuRequest,
    FoodMenuListResponse,
    UpdateFoodMenuRequest
)

router = APIRouter(prefix="/food", tags=["Food Management"])

# Role requirements
clan_admin_required = require_role([UserRole.clan_admin])
groom_access = require_role(
    [UserRole.groom, UserRole.clan_admin, UserRole.super_admin])


# ============ GROOM routes ============

# get all food types
@router.get("/menu/food_types")
def get_food_types(db: Session = Depends(get_db)):
    results = db.query(FoodMenu.food_type).distinct().all()
    return [ft[0] for ft in results]

# get all visitor counts


@router.get("/menu/visitor_options")
def get_visitor_counts(db: Session = Depends(get_db)):
    results = db.query(FoodMenu.number_of_visitors).distinct().all()
    return [vc[0] for vc in results]

# get filtered food menu based on food type, visitors, and clan_id


@router.get("/menu/{food_type}/{visitors}/{clan_id}", response_model=List[FoodMenuOut])
def get_filtered_menu(food_type: str, visitors: int, clan_id: int, db: Session = Depends(get_db)):
    # ✅ Check if clan exists
    clan_exists = db.query(Clan).filter(Clan.id == clan_id).first()
    if not clan_exists:
        raise HTTPException(
            status_code=404, detail=f"Clan with id {clan_id} not found.")

    # ✅ Check if food_type exists in DB
    food_type_exists = db.query(FoodMenu.food_type).filter(
        FoodMenu.food_type == food_type).first()
    if not food_type_exists:
        raise HTTPException(
            status_code=400, detail=f"Invalid food_type '{food_type}'.")

    # ✅ Check if number_of_visitors exists for this food_type in the same clan
    visitors_exists = (
        db.query(FoodMenu.number_of_visitors)
        .filter(FoodMenu.food_type == food_type, FoodMenu.number_of_visitors == visitors, FoodMenu.clan_id == clan_id)
        .first()
    )
    if not visitors_exists:
        raise HTTPException(
            status_code=400,
            detail=f"No menu found for {visitors} visitors in clan {clan_id} with type '{food_type}'."
        )

    # ✅ Get menus
    menus = (
        db.query(FoodMenu)
        .filter(
            FoodMenu.food_type == food_type,
            FoodMenu.number_of_visitors == visitors,
            FoodMenu.clan_id == clan_id
        )
        .all()
    )

    return menus

########## groom and clan admin routes ##################
# get all menus of a clan


@router.get("/my_menus", response_model=List[FoodMenuOut])
def get_clan_menus(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    if current.role == UserRole.super_admin:
        raise HTTPException(
            status_code=403,
            detail="super admin cant access this endpoint"
        )

    menus = db.query(FoodMenu).filter(
        FoodMenu.clan_id == current.clan_id
    ).all()

    return menus

########  Caln admin routes ##################


# creat new menu by clan admin

@router.post("/menu", response_model=dict, dependencies=[Depends(clan_admin_required)])
def create_food_menu(
    request: CreateFoodMenuRequest,
    db: Session = Depends(get_db),
    current: User = Depends(clan_admin_required)
):
    """Create a new food menu (Clan Admin only)"""

    # Ensure clan admin can only create menus for their own clan
    if request.clan_id != current.clan_id:
        raise HTTPException(
            status_code=403,
            detail=f"You can only create menus for your clan (ID: {current.clan_id})"
        )

    # Check if menu already exists for this combination
    existing_menu = db.query(FoodMenu).filter(
        FoodMenu.food_type == request.food_type,
        FoodMenu.number_of_visitors == request.number_of_visitors,
        FoodMenu.clan_id == request.clan_id
    ).first()

    if existing_menu:
        raise HTTPException(
            status_code=400,
            detail=f"Menu already exists for {request.food_type} food with {request.number_of_visitors} visitors"
        )

    # Create new menu
    menu = FoodMenu(
        food_type=request.food_type,
        number_of_visitors=request.number_of_visitors,
        menu_details=request.menu_items,

        clan_id=request.clan_id
    )

    db.add(menu)
    db.commit()
    db.refresh(menu)

    return {
        "message": "Food menu created successfully",
        "menu_id": menu.id,
        "food_type": menu.food_type,
        "visitors": menu.number_of_visitors
    }

# get menu details by menu_id


@router.get("/menu-details/{menu_id}", response_model=dict, dependencies=[Depends(clan_admin_required)])
def get_menu_details(
    menu_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(clan_admin_required)
):
    """Get detailed menu information for editing"""
    menu = db.query(FoodMenu).filter(
        FoodMenu.id == menu_id,
        FoodMenu.clan_id == current.clan_id
    ).first()

    if not menu:
        raise HTTPException(
            status_code=404,
            detail="Menu not found or you don't have permission to access it"
        )

    return {
        "id": menu.id,
        "food_type": menu.food_type,
        "number_of_visitors": menu.number_of_visitors,
        "menu_items": menu.menu_details,
        "clan_id": menu.clan_id
    }


# update existing food menu by menu_id
@router.put("/menu/{menu_id}", response_model=dict, dependencies=[Depends(clan_admin_required)])
def update_food_menu(
    menu_id: int,
    update_request: UpdateFoodMenuRequest,
    db: Session = Depends(get_db),
    current: User = Depends(clan_admin_required)
):
    """Update an existing food menu (Clan Admin only)"""

    menu = db.query(FoodMenu).filter(
        FoodMenu.id == menu_id,
        FoodMenu.clan_id == current.clan_id
    ).first()

    if not menu:
        raise HTTPException(
            status_code=404,
            detail="Menu not found "
        )

    # Update menu items
    menu.menu_details = update_request.menu_items

    menu.food_type = update_request.food_type

    menu.number_of_visitors = update_request.number_of_visitors

    db.commit()
    db.refresh(menu)

    return {
        "message": "Food menu updated successfully",
        "menu_id": menu.id,
        "food_type": menu.food_type,
        "visitors": menu.number_of_visitors
    }

# delete food menu by menu_id


@router.delete("/menu/{menu_id}", response_model=dict, dependencies=[Depends(clan_admin_required)])
def delete_food_menu(
    menu_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(clan_admin_required)
):
    """Delete a food menu (Clan Admin only)"""

    menu = db.query(FoodMenu).filter(
        FoodMenu.id == menu_id,
        FoodMenu.clan_id == current.clan_id
    ).first()

    if not menu:
        raise HTTPException(
            status_code=404,
            detail="Menu not found"
        )

    db.delete(menu)
    db.commit()

    return {
        "message": "Food menu deleted successfully",
        "deleted_menu": {
            "id": menu_id,
            "food_type": menu.food_type,
            "visitors": menu.number_of_visitors
        }
    }
# Add this route to your Python clan admin routes file


@router.get("/menus", response_model=List[dict], dependencies=[Depends(clan_admin_required)])
def list_food_menus(
    db: Session = Depends(get_db),
    current: User = Depends(clan_admin_required)
):
    """List all food menus for the current clan admin's clan"""

    menus = db.query(FoodMenu).filter(
        FoodMenu.clan_id == current.clan_id
    ).all()

    return [
        {
            "id": menu.id,
            "food_type": menu.food_type,
            "number_of_visitors": menu.number_of_visitors,
            "menu_items": menu.menu_details,
            "clan_id": menu.clan_id
        }
        for menu in menus
    ]


###

# Add these routes to your food_route.py file

# Get unique food types from current user's clan menus
@router.get("/menu/unique-food-types")
def get_unique_food_types(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Get unique food types from the current user's clan menus"""
    if current.role == UserRole.super_admin:
        raise HTTPException(
            status_code=403,
            detail="Super admin cannot access this endpoint"
        )

    # Get distinct food types from the user's clan
    results = db.query(FoodMenu.food_type).filter(
        FoodMenu.clan_id == current.clan_id
    ).distinct().all()

    food_types = [ft[0] for ft in results if ft[0]]  # Filter out None values
    return food_types


# Get unique visitor counts from current user's clan menus
@router.get("/menu/unique-visitor-counts")
def get_unique_visitor_counts(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Get unique visitor counts from the current user's clan menus"""
    if current.role == UserRole.super_admin:
        raise HTTPException(
            status_code=403,
            detail="Super admin cannot access this endpoint"
        )

    # Get distinct visitor counts from the user's clan, ordered
    results = db.query(FoodMenu.number_of_visitors).filter(
        FoodMenu.clan_id == current.clan_id
    ).distinct().order_by(FoodMenu.number_of_visitors).all()

    visitor_counts = [vc[0]
                      for vc in results if vc[0] is not None and vc[0] > 0]
    return visitor_counts
