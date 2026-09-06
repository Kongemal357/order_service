from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.infrastructure.persistence.uow import SQLAlchemyUnitOfWork, _UnitOfWorkImplementation

pytestmark = pytest.mark.asyncio


class TestUnitOfWorkImplementation:
    """Tests for _UnitOfWorkImplementation."""

    def test_uow_implementation_properties(self):
        # Given
        session = Mock()

        # When
        uow = _UnitOfWorkImplementation(session)

        # Then
        assert uow._session == session
        assert uow.order_repo is not None
        assert uow.outbox_repo is not None
        assert uow.inbox_repo is not None

    async def test_uow_implementation_commit(self):
        # Given
        session = Mock()
        session.commit = AsyncMock()
        uow = _UnitOfWorkImplementation(session)

        # When
        await uow.commit()

        # Then
        session.commit.assert_called_once()
        assert uow._committed is True

    async def test_uow_implementation_rollback(self):
        # Given
        session = Mock()
        session.rollback = AsyncMock()
        uow = _UnitOfWorkImplementation(session)

        # When
        await uow.rollback()

        # Then
        session.rollback.assert_called_once()


class TestSQLAlchemyUnitOfWork:
    """Tests for SQLAlchemyUnitOfWork."""

    @patch("src.infrastructure.persistence.uow.async_sessionmaker")
    async def test_uow_enter(self, mock_session_factory):
        # Given
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value = mock_session

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        # When
        async with uow() as uow_impl:
            # Then
            mock_session_factory.assert_called_once()
            assert isinstance(uow_impl, _UnitOfWorkImplementation)
            assert uow_impl._session == mock_session

    @patch("src.infrastructure.persistence.uow.async_sessionmaker")
    async def test_uow_commit(self, mock_session_factory):
        # Given
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value = mock_session

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        # When
        async with uow() as uow_impl:
            await uow_impl.commit()

        # Then
        mock_session.commit.assert_called_once()

    @patch("src.infrastructure.persistence.uow.async_sessionmaker")
    async def test_uow_exit_with_exception(self, mock_session_factory):
        # Given
        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value = mock_session

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        # When
        with pytest.raises(ValueError):
            async with uow():
                raise ValueError("Test error")

        # Then
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    @patch("src.infrastructure.persistence.uow.async_sessionmaker")
    async def test_uow_exit_success_with_commit(self, mock_session_factory):
        # Given
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value = mock_session

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        # When
        async with uow() as uow_impl:
            await uow_impl.commit()

        # Then
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    @patch("src.infrastructure.persistence.uow.async_sessionmaker")
    async def test_uow_exit_success_without_commit(self, mock_session_factory):
        # Given
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value = mock_session

        uow = SQLAlchemyUnitOfWork(mock_session_factory)

        # When
        async with uow():
            pass

        # Then
        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_called_once()
