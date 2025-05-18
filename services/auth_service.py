import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel # Не используется напрямую, но может быть полезно для расширения
import base64
from tonsdk.crypto import verify_sign
# PyNaCl используется под капотом библиотекой 'ton', но импорт не нужен здесь явно, если используется PublicKeyEd25519.verify

# --- JWT Configuration ---
# ВАЖНО: В реальном приложении этот ключ должен быть сложным, случайным и храниться безопасно,
# например, в переменных окружения. Не используйте этот ключ в продакшене!
SECRET_KEY = "YOUR_SUPER_SECRET_KEY_CHANGE_IN_PRODUCTION_AND_USE_ENV_VAR"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Время жизни токена в минутах

# --- Nonce Generation ---
def generate_nonce(length: int = 32) -> str:
    """Генерирует безопасную случайную строку (nonce)."""
    return secrets.token_hex(length)

# --- Token Creation ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создает JWT токен."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Если время жизни не передано, используется стандартное (15 минут)
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)}) # Добавляем время выпуска
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Signature Verification ---
def verify_ton_signature(public_key_hex: str, nonce: str, signature_b64: str) -> bool:
    try:
        public_key = bytes.fromhex(public_key_hex)
        print(f"public_key: {public_key}, len: {len(public_key)}")
        signature = base64.b64decode(signature_b64)
        print(f"signature_b64: {signature_b64}, len: {len(signature_b64)}")
        print(f"signature: {signature}, len: {len(signature)}")
        message = bytes.fromhex(nonce)
        print(f"message: {message}, len: {len(message)}")
        # return verify_sign(message, signature, public_key)
        return verify_sign(public_key, message, signature)
    except Exception as e:
        print(f"Ошибка проверки подписи: {e}")
        return False

# РИСК: Проверка соответствия адреса и публичного ключа.
# В "минимальном" примере эта функция не используется в основном потоке,
# но она критически важна для безопасности в реальном приложении.
# Без этой проверки злоумышленник может использовать свой публичный ключ
# и подпись для чужого адреса.
# from ton.utils import Address as TonUtilsAddress
# def check_address_public_key_match(
#     user_friendly_address: str,
#     public_key_hex: str,
#     workchain: int = 0, # Обычно 0 для основного блокчейна
#     # testnet: bool = False # Укажите, если работаете с testnet
# ) -> bool:
#     """
#     Проверяет, соответствует ли данный user-friendly адрес указанному публичному ключу.
#     Это УПРОЩЕННЫЙ пример. Реальная проверка может быть сложнее из-за разных
#     типов кошельков и флагов адресов (bounceable/non-bounceable).
#     """
#     try:
#         pk_bytes = bytes.fromhex(public_key_hex)
#         ton_pk_obj = PublicKeyEd25519(pk_bytes)
#
#         # Генерируем адрес из публичного ключа для разных флагов bounceable
#         # и сравниваем с предоставленным адресом.
#         # Библиотека `ton` генерирует адреса с определенными флагами по умолчанию.
#         # Нужно убедиться, что сравнение корректно для всех форматов адресов,
#         # которые может прислать фронтенд.
#
#         # Пример для bounceable адреса (наиболее распространенный)
#         generated_address_bounceable = TonUtilsAddress.from_public_key(
#             ton_pk_obj,
#             workchain=workchain,
#             # По умолчанию is_bounceable=True для from_public_key в некоторых версиях/контекстах
#         )
#         # Пример для non-bounceable адреса
#         # (требует другого способа генерации или явного указания флагов, если поддерживается)
#
#         # Приводим оба адреса к одному формату для сравнения
#         # (например, user-friendly, bounceable, mainnet)
#         # TonUtilsAddress(user_friendly_address).to_string(is_user_friendly=True, is_bounceable=True) == \
#         # generated_address_bounceable.to_string(is_user_friendly=True, is_bounceable=True)
#
#         # Очень упрощенная проверка (может не покрывать все случаи):
#         # Сгенерируем адрес по умолчанию и сравним.
#         # Фронтенд должен присылать адрес в том формате, который мы ожидаем или можем сгенерировать.
#         addr_from_pk = TonUtilsAddress.from_public_key(ton_pk_obj, workchain) # по умолчанию bounceable
#         parsed_user_addr = TonUtilsAddress(user_friendly_address)
#
#         # Сравнение "сырых" хеш-частей адресов может быть более надежным, если workchain совпадает
#         return parsed_user_addr.hash_part == addr_from_pk.hash_part and \
#                parsed_user_addr.workchain == addr_from_pk.workchain
#
#     except Exception as e:
#         print(f"Address-PublicKey match check failed: {e}")
#         return False
#     return False # Заглушка, если не реализовано полностью

# --- JWT Middleware (новое) ---
from fastapi import Request, HTTPException, status # Добавлено для middleware
from schemas.auth import TokenData # Добавлено для middleware, предполагаем, что schemas доступен напрямую

async def jwt_auth_middleware(request: Request, call_next):
    """
    Middleware для проверки JWT.
    Пропускает публичные пути, для остальных проверяет 'Authorization: Bearer <token>'.
    В случае успеха добавляет request.state.user.
    """
    # Список публичных путей, которые не требуют JWT аутентификации
    public_paths = [
        "/", # Если есть корневой путь
        "/docs",
        "/openapi.json",
        "/api/auth/request_nonce",
        "/api/auth/verify_signature",
        # Добавьте другие публичные пути вашего приложения, если они есть, например, /api/risk, если он публичный
        # Если /api/risk должен быть защищен, то он НЕ должен быть в этом списке.
    ]

    # Проверяем, является ли текущий путь одним из публичных
    # или начинается с одного из них (например, /docs/*)
    is_public_path = False
    for path in public_paths:
        if request.url.path == path or (path.endswith('/') and request.url.path.startswith(path)):
            is_public_path = True
            break
    
    # Также часто /static/ пути делают публичными
    if request.url.path.startswith("/static"):
        is_public_path = True

    if is_public_path:
        response = await call_next(request)
        return response

    # Если путь не публичный, продолжаем проверку токена
    token_str = request.headers.get("Authorization")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token_str:
        raise credentials_exception # Токен отсутствует

    parts = token_str.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise credentials_exception # Некорректный формат токена

    token = parts[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_address: Optional[str] = payload.get("sub") # 'sub' содержит адрес пользователя
        if user_address is None:
            # Если 'sub' отсутствует или None, это может быть невалидный токен
            # или токен, сгенерированный не нашим сервисом по ожидаемому формату.
            raise credentials_exception
        
        # Сохраняем данные пользователя в состоянии запроса
        # В эндпоинтах можно будет получить доступ через request.state.user
        request.state.user = TokenData(address=user_address)
    except JWTError as e:
        print(f"JWT decoding/validation error: {e}") # Для отладки
        raise credentials_exception # Ошибка декодирования или невалидный токен
    
    response = await call_next(request)
    return response