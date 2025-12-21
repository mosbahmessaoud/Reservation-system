"""
Super Admin routes: manage counties, clans, clan admins.
"""
from server.auth_utils import generate_access_password, hash_access_password
from server.schemas.user import AccessPasswordCreate, AccessPasswordResponse
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from server.models.food import FoodMenu
from server.schemas.notification import NotifDataCreat
from server.utils.notification_service import NotificationService
from server.utils.otp_utils import generate_otp_code
from server.utils.phone_utils import validate_number_phone, validate_number_phone_of_guardian

from ..models.clan_rules import ClanRules
from ..models.clan_settings import ClanSettings
from ..models.committee import HaiaCommittee, MadaehCommittee
from ..models.hall import Hall
from ..schemas.haia_committe import HaiaCreate, HaiaOut, HaiaUpdate
from ..schemas.madaih_committe import MadaihCreate, MadaihOut, MadaihUpdate
from ..auth_utils import get_current_user, get_db, require_role, get_password_hash
from ..models.user import UserRole, User, UserStatus
from ..models.county import County
from ..models.clan import Clan
from ..schemas.county import CountyCreate, CountyOut, CountyUpdate
from ..schemas.clan import ClanCreate, ClanOut, ClanUpdate
from ..schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(
    prefix="/super-admin",
    tags=["super-admin"]
)

# super_admin_required = require_role([UserRole.super_admin])
super_admin_required = require_role("super_admin")


####################### Counties CRUD  #####################

# creat new county


@router.post("/county", response_model=CountyOut, dependencies=[Depends(super_admin_required)])
def create_county(county: CountyCreate, db: Session = Depends(get_db)):
    print("Creating county------------------------------------------------------")
    existing = db.query(County).filter(County.name == county.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="County already exists")
    obj = County(name=county.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

# get all counties


@router.get("/counties", response_model=list[CountyOut], dependencies=[Depends(super_admin_required)])
def list_counties(db: Session = Depends(get_db)):
    return db.query(County).all()


# updating a county
@router.put("/county/{county_id}", response_model=CountyOut, dependencies=[Depends(super_admin_required)])
def update_county(county_id: int, county_data: CountyUpdate, db: Session = Depends(get_db)):
    county = db.query(County).filter(
        County.id == county_id
    ).first()
    if not county:
        raise HTTPException(status_code=404, detail="county not found")

    # for field, value in county_data.dict(exclude_unset=True).items():
    #     setattr(county, field, value)
    county.name = county_data.name
    db.commit()
    db.refresh(county)
    return county


# delete a county
@router.delete("/county/{county_id}", response_model=dict, dependencies=[Depends(super_admin_required)])
def deleat_a_county(county_id: int, db: Session = Depends(get_db)):
    county = db.query(County).filter(
        County.id == county_id
    ).first()
    if not county:
        raise HTTPException(status_code=404, detail=" county not found")

    db.delete(county)
    db.commit()
    return {"message": f"county id {county_id} has been deleted successfully."}
# --------------------------------------------------------


############################ clan CRUD #############################
# creating new caln


@router.post("/clan", response_model=ClanOut, dependencies=[Depends(super_admin_required)])
def create_clan(clan: ClanCreate, db: Session = Depends(get_db)):
    # Check if a clan with the same name already exists in the same county
    existing = db.query(Clan).filter(
        and_(
            Clan.name == clan.name,
            Clan.county_id == clan.county_id  # Match county_id, not Clan.id
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Clan already exists")
    check_county = db.query(County).filter(
        County.id == clan.county_id,
    ).first()
    if not check_county:
        raise HTTPException(
            status_code=404, detail=f"the county with this id {clan.county_id} not found !!! ")
    clane = Clan(name=clan.name, county_id=clan.county_id)
    db.add(clane)
    db.commit()
    db.refresh(clane)
    settings = ClanSettings(clan_id=clane.id)
    db.add(settings)
    db.commit()
    # Create default clan rules
    # default_rules = ClanRules(
    #     general_rule="القوانين العامة للعشيرة",
    #     groom_supplies="متطلبات العريس",
    #     rule_about_clothing="قواعد الملابس",
    #     rule_about_kitchenware="قواعد أدوات المطبخ",
    #     clan_id=clane.id
    # )
    # db.add(default_rules)
    hall_name = " دار " + clan.name
    hall = Hall(name=hall_name, capacity=000, clan_id=clane.id)
    db.add(hall)
    db.commit()

    # Create default food menus
    # food_menu = FoodMenu(
    #     food_type="Traditional",
    #     number_of_visitors=100,
    #     menu_details=[
    #         "33kg بطاطس (Potatoes)",
    #         "23kg طماطم (Tomatoes)",
    #         "15kg بصل (Onions)",
    #         "37kg أرز (Rice)"

    #     ],
    #     clan_id=clane.id
    # )
    # db.add(food_menu)
    # db.commit()

    return clane


# geting all clans
@router.get("/clans/{county__id}", response_model=list[ClanOut], dependencies=[Depends(super_admin_required)])
def list_clans(county__id: int, db: Session = Depends(get_db)):
    clans = db.query(Clan).filter(
        Clan.county_id == county__id).all()
    if not clans:
        raise HTTPException(status_code=404, detail="dost exist any clan ")
    return clans


# update a caln info
@router.put("/clan/{clan_id}", response_model=ClanOut, dependencies=[Depends(super_admin_required)])
def update_clan(clan_id: int, clan_data: ClanUpdate, db: Session = Depends(get_db)):
    """
    Update a clan's information (Super Admin only).
    """
    clan = db.query(Clan).filter(Clan.id == clan_id).first()
    if not clan:
        raise HTTPException(
            status_code=404, detail=f"Clan with this id {clan_id} not found")

    check_county = db.query(County).filter(
        County.id == clan_data.county_id
    ).first()
    if not check_county:
        raise HTTPException(
            status_code=404, detail=f"County with this id {clan_data.county_id} not found")

    for field, value in clan_data.dict(exclude_unset=True).items():
        setattr(clan, field, value)

    db.commit()
    db.refresh(clan)
    return clan


# delet a clan
@router.delete("/clan/{clan_id}", response_model=dict, dependencies=[Depends(super_admin_required)])
def delet_a_clan(clan_id: int, db: Session = Depends(get_db)):
    clan = db.query(Clan).filter(
        Clan.id == clan_id
    ).first()
    if not clan:
        raise HTTPException(status_code=404, detail="clan not found")
    db.delete(clan)
    db.commit()

    return {"message": f"Clan with ID {clan_id} has been deleted successfully."}


# get all clans
@router.get("/all_clans", response_model=list[ClanOut])
def get_all_clans(db: Session = Depends(get_db)):
    """
    Get all clans.
    """
    clans = db.query(Clan).all()
    if not clans:
        raise HTTPException(status_code=404, detail="No clans found")
    return clans
# --------------------------------------------------------


################################## Clan Admin CRUD ##########################


@router.post("/create-clan-admin", response_model=UserOut, dependencies=[Depends(super_admin_required)])
def create_clan_admin_account(user_in: UserCreate, db: Session = Depends(get_db)):
    # make sure one clan admin per clan
    if user_in.clan_id is None:
        raise HTTPException(
            status_code=400, detail="Clan ID is required for clan admin")

    # if user_in.role != UserRole.clan_admin:
    #     raise HTTPException(status_code=400, detail="Role must be clan_admin")

        # Check if user is already a clan admin
    existing_user = db.query(User).filter(
        and_(
            User.phone_number == user_in.phone_number,
            User.role == UserRole.clan_admin
        )
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400, detail="User is already exists as a clan admin")

    # Check if phone number already exists
    existing = db.query(User).filter(
        User.phone_number == user_in.phone_number).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="Phone number already registered")

    check_county = db.query(County).filter(
        County.id == user_in.county_id
    ).first()
    if not check_county:
        raise HTTPException(
            status_code=404, detail=f"County with this id {user_in.county_id} dosnt exist !! ")

    # Check if clan exists
    clan = db.query(Clan).filter(Clan.id == user_in.clan_id).first()
    if not clan:
        raise HTTPException(status_code=404, detail="Clan not found")

    # Check if user already exists in the clan
    existing_clan_admin = db.query(User).filter(
        and_(
            User.clan_id == user_in.clan_id,
            User.role == UserRole.clan_admin
        )
    ).first()
    # if existing_clan_admin:
    #     raise HTTPException(
    #         status_code=400, detail="Clan already has a clan admin")

    # Hash the password
    if not user_in.password:
        raise HTTPException(status_code=400, detail="Password is required")

    hashed_pw = get_password_hash(user_in.password)
    otp_code = generate_otp_code()
    validate_number_phone(user_in.phone_number)
    admin = User(
        phone_number=user_in.phone_number,
        password_hash=hashed_pw,
        role=UserRole.clan_admin,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        father_name=user_in.father_name,
        grandfather_name=user_in.grandfather_name,
        birth_date=user_in.birth_date,
        birth_address=user_in.birth_address,
        home_address=user_in.home_address,
        clan_id=user_in.clan_id,
        county_id=user_in.county_id,
        # New fields from updated model
        otp_code=otp_code,
        otp_expiration=datetime.utcnow() + timedelta(hours=2),
        created_at=datetime.utcnow(),
        status=UserStatus.active
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


# get all clan admins by county_id
@router.get("/clan-admins/{county__id}", response_model=list[UserOut], dependencies=[Depends(super_admin_required)])
def list_clan_admins(county__id: int, db: Session = Depends(get_db)):
    check_county = db.query(County).filter(
        County.id == county__id
    ).first()
    if not check_county:
        raise HTTPException(
            status_code=404, detail=f"County with this id {county__id} dosnt exist !! ")
    return db.query(User).filter(
        User.role == UserRole.clan_admin,
        User.county_id == county__id
    ).all()


# delet a clan admin
@router.delete("/clan-admins/{id}", dependencies=[Depends(super_admin_required)])
def delete_clan_admin(id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(
        (
            User.id == id
            # User.role == UserRole.clan_admin
        )
    ).first()
    # Check if admin exists

    if not admin:
        raise HTTPException(
            status_code=404, detail=f"user with this id {id} ,not found")
    if admin.role != UserRole.clan_admin:
        raise HTTPException(
            status_code=400, detail="User is not a clan admin")

    db.delete(admin)
    db.commit()
    return {"detail": f"Clan admin with this id {id} deleted successfully"}


# update the clan admin info

@router.put("/clan-admins/{admin_id}", response_model=UserOut, dependencies=[Depends(super_admin_required)])
def update_clan_admin(admin_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Clan Admin.
    - Only Super Admin can perform this.
    - Ensures phone_number uniqueness.
    - Optionally update password, clan, and personal info.
    """
    # Find the clan admin by ID
    admin = db.query(User).filter(
        and_(
            User.id == admin_id,
            User.role == UserRole.clan_admin
        )
    ).first()

    if not admin:
        raise HTTPException(
            status_code=404,
            detail=f"Clan admin with id {admin_id} not found"
        )

    # # Check if phone number is already taken by another user
    # if user_in.phone_number and user_in.phone_number != admin.phone_number:
    #     phone_check = db.query(User).filter(

    #         User.phone_number == user_in.phone_number,
    #         User.id != admin_id

    #     ).first()
    #     if phone_check:
    #         raise HTTPException(
    #             status_code=400,
    #             detail="Phone number already registered"
    #         )

    if user_in.county_id:
        check_county = db.query(County).filter(
            County.id == user_in.county_id
        ).first()
        if not check_county:
            raise HTTPException(
                status_code=404, detail=f"County with this id {user_in.county_id} dosnt exist !! ")

    # If clan_id is being updated, verify clan exists
    if user_in.clan_id and user_in.clan_id != admin.clan_id:
        clan = db.query(Clan).filter(Clan.id == user_in.clan_id).first()
        if not clan:
            raise HTTPException(status_code=404, detail="Clan not found")
        # Check if the new clan already has a clan admin
        existing_admin = db.query(User).filter(
            and_(
                User.clan_id == user_in.clan_id,
                User.role == UserRole.clan_admin,
                User.id != admin_id
            )
        ).first()
        if existing_admin:
            raise HTTPException(
                status_code=400,
                detail="This clan already has a clan admin"
            )
        admin.clan_id = user_in.clan_id

    # Update password if provided
    if user_in.password:
        admin.password_hash = get_password_hash(user_in.password)

    # Update other fields if provided
    update_fields = [
        "phone_number", "first_name", "last_name", "father_name",
        "grandfather_name", "birth_date", "birth_address", "home_address"
    ]
    for field in update_fields:
        value = getattr(user_in, field, None)
        if value is not None:
            setattr(admin, field, value)

    db.commit()
    db.refresh(admin)
    return admin

# --------------------------------------------------------


# Get clan admin by ID
@router.get("/clan-admins/detail/{admin_id}", response_model=UserOut, dependencies=[Depends(super_admin_required)])
def get_clan_admin_by_id(admin_id: int, db: Session = Depends(get_db)):
    """
    Get a specific clan admin by ID.
    - Only Super Admin can access this.
    """
    admin = db.query(User).filter(
        and_(
            User.id == admin_id,
            User.role == UserRole.clan_admin
        )
    ).first()

    if not admin:
        raise HTTPException(
            status_code=404,
            detail=f"Clan admin with id {admin_id} not found"
        )

    return admin


# active and disactive the clan admin account


@router.put("/change_status/{admin_id}", response_model=UserOut, dependencies=[Depends(super_admin_required)])
def change_clan_admin_status(admin_id: int, db: Session = Depends(get_db)):
    clan_admin = db.query(User).filter(
        User.id == admin_id,
        User.role == UserRole.clan_admin
    ).first()

    if not clan_admin:
        raise HTTPException(
            status_code=404, detail=f"clan admin with this id {admin_id} not found !! ")

    if clan_admin.status == UserStatus.active:
        clan_admin.status = UserStatus.inactive
    else:
        clan_admin.status = UserStatus.active

    db.commit()
    db.refresh(clan_admin)

    # Return the full user object instead of just a message
    return clan_admin
########################### haia CRUD ############################

# post new haia


@router.post("/haia", response_model=HaiaCreate, dependencies=[Depends(super_admin_required)])
def create_ceremony_committee(c: HaiaCreate, db: Session = Depends(get_db)):
    check_county = db.query(County).filter(
        County.id == c.county_id
    ).first()
    if not check_county:
        raise HTTPException(
            status_code=404, detail=f"County with this id {c.county_id} dosnt exist !! ")

    obj = HaiaCommittee(name=c.name, county_id=c.county_id)
    exist_committ_check = db.query(HaiaCommittee).filter(
        HaiaCommittee.county_id == obj.county_id,
        HaiaCommittee.name == obj.name
    ).first()
    if exist_committ_check:
        raise HTTPException(status_code=400, detail="alredy exist")
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

# update haia


@router.put("/haia/{haia__id}/{county__id}", response_model=HaiaOut, dependencies=[Depends(super_admin_required)])
def update_the_haia(haia__id: int, county__id: int, haia_data: HaiaUpdate, db: Session = Depends(get_db)):
    check_county = db.query(County).filter(
        County.id == county__id
    ).first()
    if not check_county:
        raise HTTPException(
            status_code=404, detail=f"County with this id {county__id} dosnt exist !! ")

    haia = db.query(HaiaCommittee).filter(
        HaiaCommittee.id == haia__id,
        HaiaCommittee.county_id == county__id
    ).first()
    if not haia:
        raise HTTPException(
            status_code=404, detail=f"haia with this {haia__id} id not found")
    haia.name = haia_data.name
    db.commit()
    db.refresh(haia)
    return haia


# delet haia


@router.delete("/haia/{haia__id}/{county__id}", dependencies=[Depends(super_admin_required)])
def delet_haia(haia__id: int, county__id: int, db: Session = Depends(get_db)):
    check_county = db.query(County).filter(
        County.id == county__id
    ).first()
    if not check_county:
        raise HTTPException(
            status_code=404, detail=f"County with this id {county__id} dosnt exist !! ")

    haia = db.query(HaiaCommittee).filter(
        HaiaCommittee.id == haia__id,
        HaiaCommittee.county_id == county__id
    ).first()
    if not haia:
        raise HTTPException(
            status_code=404, detail=f"haia with this {haia__id} id not found")
    db.delete(haia)
    db.commit()
    return {"message": f"the haia with this id {haia__id} has been deleted seccessfelly."}

# get  all haiats by county_id


@router.get("/haia/{county__id}", response_model=list[HaiaOut], dependencies=[Depends(super_admin_required)])
def list_of_all_haia(county__id: int, db: Session = Depends(get_db)):
    return db.query(HaiaCommittee).filter(HaiaCommittee.county_id == county__id).all()


# --------------------------------------------------------

## 2######################### madaih_committe CRUD ############################

# post new madaih_committe
@router.post("/madaih_committe", response_model=MadaihCreate, dependencies=[Depends(super_admin_required)])
def create_madaih_committee(c: MadaihCreate, db: Session = Depends(get_db)):
    check_county = db.query(County).filter(
        County.id == c.county_id
    ).first()
    if not check_county:
        raise HTTPException(
            status_code=404, detail=f"County with this id {c.county_id} dosnt exist !! ")

    obj = MadaehCommittee(name=c.name, county_id=c.county_id)
    exist_committ_check = db.query(MadaehCommittee).filter(
        MadaehCommittee.county_id == obj.county_id,
        MadaehCommittee.name == obj.name
    ).first()
    if exist_committ_check:
        raise HTTPException(status_code=400, detail="alredy exist")
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

# update madaih


@router.put("/madaih_committe/{madaih__id}/{county__id}", response_model=MadaihOut, dependencies=[Depends(super_admin_required)])
def update_the_madaih(madaih__id: int, county__id: int, madaih_data: MadaihUpdate, db: Session = Depends(get_db)):
    check_county = db.query(County).filter(
        County.id == county__id
    ).first()
    if not check_county:
        raise HTTPException(
            status_code=404, detail=f"County with this id {county__id} dosnt exist !! ")

    madaih = db.query(MadaehCommittee).filter(
        MadaehCommittee.id == madaih__id,
        MadaehCommittee.county_id == county__id
    ).first()
    if not madaih:
        raise HTTPException(
            status_code=404, detail=f"madaih with this {madaih__id} id not found")

    madaih.name = madaih_data.name
    db.commit()
    db.refresh(madaih)
    return madaih

# delet Madaih


@router.delete("/madaih_committe/{madaih__id}/{county__id}", dependencies=[Depends(super_admin_required)])
def delet_madaih(madaih__id: int, county__id: int, db: Session = Depends(get_db)):
    check_county = db.query(County).filter(
        County.id == county__id
    ).first()
    if not check_county:
        raise HTTPException(
            status_code=404, detail=f"County with this id {county__id} dosnt exist !! ")

    madaih = db.query(MadaehCommittee).filter(
        MadaehCommittee.id == madaih__id,
        MadaehCommittee.county_id == county__id
    ).first()
    if not madaih:
        raise HTTPException(
            status_code=404, detail=f"madaih with this {madaih__id} id not found")
    db.delete(madaih)
    db.commit()
    return {"message": f"the madaih with this id {madaih__id} has been deleted seccessfelly."}

# get  all Madaeh  by county_id


@router.get("/madaih_committe/{county__id}", response_model=list[MadaihOut], dependencies=[Depends(super_admin_required)])
def list_of_all_madaih_committe(county__id: int, db: Session = Depends(get_db)):
    return db.query(MadaehCommittee).filter(MadaehCommittee.county_id == county__id).all()


# --------------------------------------------------------


# Generate access password for clan admin (Super Admin only)
@router.post("/clan-admin/{admin_id}/generate-access-password",
             response_model=AccessPasswordResponse,
             dependencies=[Depends(super_admin_required)])
def generate_clan_admin_access_password(
    admin_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate a new access password for a clan admin.
    Super Admin only.
    """
    # Find clan admin
    admin = db.query(User).filter(
        User.id == admin_id,
        User.role == UserRole.clan_admin
    ).first()

    if not admin:
        raise HTTPException(
            status_code=404,
            detail=f"مسؤول العشيرة بالمعرف {admin_id} غير موجود"
        )

    # Generate new password
    new_password = generate_access_password(length=8)

    # Hash and save
    admin.access_pages_password_hash = hash_access_password(new_password)

    db.commit()
    db.refresh(admin)

    return {
        "message": "تم إنشاء كلمة مرور الوصول بنجاح",
        "user_id": admin.id,
        "generated_password": new_password  # Show once!
    }

# Manually set access password for clan admin


@router.put("/clan-admin/{admin_id}/set-access-password",
            response_model=dict,
            dependencies=[Depends(super_admin_required)])
def set_clan_admin_access_password(
    admin_id: int,
    password_data: AccessPasswordCreate,
    db: Session = Depends(get_db)
):
    """
    Manually set access password for clan admin.
    Super Admin only.
    """
    admin = db.query(User).filter(
        User.id == admin_id,
        User.role == UserRole.clan_admin
    ).first()

    if not admin:
        raise HTTPException(
            status_code=404,
            detail=f"مسؤول العشيرة بالمعرف {admin_id} غير موجود"
        )

    # Hash and save the provided password
    admin.access_pages_password_hash = hash_access_password(
        password_data.access_password)

    db.commit()

    return {
        "message": "تم تعيين كلمة مرور الوصول بنجاح",
        "user_id": admin.id
    }
