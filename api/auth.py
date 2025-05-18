from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta

# Используем прямые импорты, так как файлы находятся в пакетах
from schemas.auth import NonceResponse, VerifySignatureRequest, Token
from services import auth_service

router = APIRouter()

@router.get("/request_nonce", response_model=NonceResponse, summary="Request a Nonce for Signing")
async def request_nonce_endpoint():
    """
    Предоставляет клиенту случайную строку (nonce), которую клиент должен подписать своим TON-кошельком.
    """
    nonce = auth_service.generate_nonce()
    return NonceResponse(nonce=nonce)

@router.post("/verify_signature", response_model=Token, summary="Verify Signature and Get JWT")
async def verify_signature_and_get_token_endpoint(request_data: VerifySignatureRequest):
    """
    Проверяет подпись nonce, сделанную TON-кошельком.
    Если подпись верна, возвращает JWT-токен.

    - **address**: Адрес TON-кошелька пользователя (user-friendly формат).
    - **public_key**: Публичный ключ кошелька в HEX-формате.
    - **nonce**: Nonce, полученный ранее от `/request_nonce`.
    - **signature**: Подпись nonce в Base64-формате.
    """

    # РИСК БЕЗОПАСНОСТИ: ОТСУТСТВИЕ ПРОВЕРКИ СООТВЕТСТВИЯ АДРЕСА И ПУБЛИЧНОГО КЛЮЧА
    # ВАЖНО: В реальном приложении здесь КРИТИЧЕСКИ ВАЖНО проверить, что предоставленный `public_key`
    # действительно соответствует `address` пользователя. Без этой проверки злоумышленник может:
    # 1. Указать ЧУЖОЙ `address`.
    # 2. Предоставить СВОЙ `public_key`.
    # 3. Подписать `nonce` СВОИМ приватным ключом.
    # Если проверка подписи (`verify_ton_signature`) пройдет успешно (т.к. `public_key` и `signature` корректны),
    # и затем `address` (чужой) будет использован для создания JWT, то злоумышленник получит токен
    # от имени другого пользователя.
    #
    # Пример такой проверки (auth_service.check_address_public_key_match) закомментирован
    # в auth_service.py и требует тщательной реализации и тестирования для различных форматов адресов.
    # Для "минимального" примера эта проверка опущена, но это ЗНАЧИТЕЛЬНЫЙ РИСК.
    # if not auth_service.check_address_public_key_match(request_data.address, request_data.public_key):
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Address does not match the public key. This is a security risk.",
    #     )

    is_signature_valid = auth_service.verify_ton_signature(
        public_key_hex=request_data.public_key,
        nonce=request_data.nonce,
        signature_b64=request_data.signature
    )

    if not is_signature_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature, public key, or nonce. Verification failed.",
            headers={"WWW-Authenticate": "Bearer"}, # Стандартный заголовок для 401
        )

    # Если подпись верна, создаем JWT токен
    # 'sub' (subject) - стандартное поле для идентификатора пользователя в JWT.
    # Также можно добавить другие кастомные поля, если необходимо.
    token_data = {
        "sub": request_data.address, # Адрес кошелька как основной идентификатор
        "user_address": request_data.address, # Можно дублировать или использовать другие поля
        # "public_key": request_data.public_key # Можно добавить публичный ключ в токен, если нужно
    }
    
    access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")