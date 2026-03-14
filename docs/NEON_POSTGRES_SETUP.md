# Neon PostgreSQL Setup

## Muc tieu

Bat backend luu tru messaging session/tree/message log len Neon PostgreSQL thay vi file JSON local.

Backend se tu dong chon PostgreSQL khi bien moi truong `DATABASE_URL` duoc set.

## 1) Cau hinh DATABASE_URL

Khong commit secret vao git. Hay dat connection string trong file `.env` local (hoac bien moi truong he thong):

```dotenv
DATABASE_URL="postgresql://<user>:<password>@<host>/<db>?sslmode=require&channel_binding=require"
```

`DATABASE_URL` da duoc ho tro trong [config/settings.py](config/settings.py).

## 2) Cac file da duoc noi vao app

- Chon session store theo `DATABASE_URL`:
  - [api/app.py](api/app.py)
- Backend store PostgreSQL moi:
  - [messaging/postgres_session.py](messaging/postgres_session.py)
- Bien mau moi truong:
  - [config/env.example](config/env.example)
- Dependency PostgreSQL driver:
  - [pyproject.toml](pyproject.toml)

## 3) Tu dong tao bang

Khi app khoi dong voi `DATABASE_URL`, he thong tu tao cac bang sau neu chua ton tai:

- `fcc_session_trees`
- `fcc_session_node_map`
- `fcc_session_message_log`

Ban khong can migration thu cong cho phase nay.

## 4) Kiem tra app da dung PostgreSQL

Khi start server, log se hien 1 trong 2 dong:

- `Using PostgreSQL session store`
- `Using file-based session store`

Neu thay dong dau, toan bo session state dang luu tren Neon.

## 5) Luu y bao mat

- Neu connection string da tung bi lo, hay rotate password trong Neon dashboard.
- Khong push `DATABASE_URL` that vao repo.
- Uu tien dung secret manager tren production.

## 6) Gioi han pham vi phien ban nay

Session store PostgreSQL hien bao gom:

- Conversation trees
- Node -> tree mapping
- Message log phuc vu `/clear`

Cac domain business data Jira/Calendar/workflow se duoc them o buoc tiep theo (bang rieng, migration rieng).
