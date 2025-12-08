from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from storage.db.interface.base import BaseInterface
from storage.db.models import (AuthProvider, TempOTPStorage, User, UserAuth,
                               UserProfile)


class UsersDBInterface(BaseInterface):
    def __init__(self, session_):
        super().__init__(session_=session_)

    async def get_user_by_id(self, user_id: int):
        return await self.get_row(User, id=user_id)

    async def _create_user_auth(
        self,
        session: AsyncSession,
        user_id: int,
        provider_slug: str,
        subject: str,
        token: Optional[str] = None,
    ):
        provider = await session.scalar(
            select(AuthProvider).where(AuthProvider.slug == provider_slug)
        )
        if not provider:
            raise ValueError("Provider not found")
        elif not provider.enable:
            raise ValueError("Provider not available")
        exist_auth_with_provider: UserAuth | None = await session.scalar(
            select(UserAuth).where(
                UserAuth.user_id == user_id, UserAuth.provider_id == provider.id
            )
        )
        if exist_auth_with_provider:
            exist_auth_with_provider.subject = subject
            exist_auth_with_provider.token = token
        else:
            user_auth = UserAuth(
                user_id=user_id, provider_id=provider.id, subject=subject, token=token
            )
            session.add(user_auth)

    async def _create_user_full(
        self,
        session: AsyncSession,
        provider_slug: str,
        subject: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        token: Optional[str] = None,
    ) -> User:
        user_model = User()
        session.add(user_model)
        await session.flush()
        profile_data = {}
        if provider_slug == "telegram":
            profile_data["username"] = username
            profile_data["first_name"] = first_name
            profile_data["last_name"] = last_name
            profile_data["phone"] = phone
        elif provider_slug == "email":
            profile_data["email"] = subject
        profile_model = UserProfile(
            user_id=user_model.id,
            **profile_data,
        )
        session.add(profile_model)

        await self._create_user_auth(
            session=session,
            user_id=user_model.id,
            provider_slug=provider_slug,
            subject=subject,
            token=token,
        )
        await session.commit()
        user_stmt = select(User).where(User.id == user_model.id)
        return await session.scalar(user_stmt)

    async def bind_login(
        self,
        user_id: int,
        provider_slug: str,
        subject: str,
        username: Optional[str] = None,
        token: Optional[str] = None,
    ):
        async with self.async_ses() as session:
            await self._create_user_auth(
                session=session,
                user_id=user_id,
                provider_slug=provider_slug,
                subject=subject,
                token=token,
            )
            upd_profile_data = {}
            if username:
                upd_profile_data["username"] = username
            if provider_slug == "email":
                upd_profile_data["email"] = subject
            if upd_profile_data:
                await self.update_rows(
                    UserProfile,
                    session=session,
                    filter_by={"user_id": user_id},
                    **upd_profile_data,
                )
            await session.commit()

    async def edit_password(self, user_id: int, subject: str, password: str):
        async with self.async_ses() as session:
            await self.update_rows(
                UserAuth,
                session=session,
                filter_by={"user_id": user_id, "subject": subject},
                token=password,
            )

    async def get_or_create_user_by_auth(
        self,
        provider_slug: str,
        subject: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        token: Optional[str] = None,
        create: bool = False,
        filter_with_token: bool = True,
    ) -> Optional[User]:
        async with self.async_ses() as session:
            user_auth_stmt = (
                select(UserAuth)
                .options(selectinload(UserAuth.user).options(selectinload(User.auths)))
                .where(
                    UserAuth.subject == subject,
                    UserAuth.token == token if filter_with_token else True,
                    UserAuth.provider.has(AuthProvider.slug == provider_slug),
                )
            )
            user_auth: Optional[UserAuth] = await session.scalar(user_auth_stmt)
            if user_auth:
                return user_auth.user
            if create:
                return await self._create_user_full(
                    session=session,
                    provider_slug=provider_slug,
                    subject=subject,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    token=token,
                )

    async def update_temp_otp(self, subject: str, confirmed=False, code: str = None):
        async with self.async_ses() as session:
            exist_row = await session.scalar(
                select(TempOTPStorage).filter_by(subject=subject)
            )
            if exist_row:
                await session.execute(
                    update(TempOTPStorage)
                    .filter_by(id=exist_row.id)
                    .values(otp_code=code, confirmed=confirmed)
                )
            else:
                session.add(
                    TempOTPStorage(subject=subject, otp_code=code, confirmed=confirmed)
                )
            await session.commit()

    async def delete_temp_otp(self, otp_storage_id: int):
        await self.delete_rows(TempOTPStorage, id=otp_storage_id)

    async def get_temp_otp(self, subject: str):
        return await self.get_row(TempOTPStorage, subject=subject)
