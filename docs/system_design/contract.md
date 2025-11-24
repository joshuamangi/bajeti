# Contract / API / System Interface

This document describes the contract between the User and the System

## HTTP Requests

### AUTH [ /api/auth ]

#### POST / [ register ]

``` json
body : {
    "first_name": string,
    "last_name": string,
    "email": string,
    "security_answer": string,
}
```

#### POST /token [ login ]

``` json
body : {
    "email": string,
    "password": string,
}
```

#### GET /users/me [ current user ]

``` json
get_current_user()
```

### USERS [ /api/users ]

#### POST /password/reset [ password reset ]

``` json
body : {
    "email": string,
    "password": string,
    "security_ansswer": string
}
```

#### PUT /me [ update user ]

``` json
body : {
    "id": string,
    "first_name": Optional,
    "last_name": Optional,
    "email": Optional,
    "security_answer": Optional
}
```

### CATEGORIES [ /api/categories ]

#### POST / [ create category ]

``` json
body : {
    "name": string,
    "limit_amount": float
}
```

#### PUT /category_id [ update category ]

``` json
body : {
    "id" : string,
    "name": Optional,
    "limit_amount": Optional,
    "updated_at": datetime
}
```

#### DELETE /category_id [ deletes category ]

``` json
body : {
    "id": string
}
```

#### GET /category_id [ Fetch categories ]

``` json
body : {
    "id": int,
    "name": string,
    "limit_amout": string,
    "user_id": int,
    "created_at": datetime,
    "updated_at": datetime
}
```

#### GET /with-stats [ categories with stats ]

``` json
body: {
    "expense_count": int,
    "balance": float,
    "expenses": List[
        {
            "id": int,
            "name": string,
            "updated_at": datetime,
            "created_at": datetime
        }
    ]
}
```

### EXPENSES [ api/expenses]

#### POST / [ create expense ]

``` json
body : {
    "user_id": int,
    "amount": float,
    "description": string,
    "month": string,
}
```

## SYSTEM Responses
