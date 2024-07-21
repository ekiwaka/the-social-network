# the-social-network

This project is a microservice-based social media platform built with Flask, MySQL, and Elasticsearch. It allows users to sign up, create discussions, comment on discussions, like discussions, and search for posts using hashtags.

## Project Structure

The project is divided into the following microservices:
- User Service
- Discussion Service
- Comment Service
- Like Service
- Search Service
- API Gateway

## Features

1. User can sign up/login.
2. User can create/update/delete discussions.
3. User can comment on discussions.
4. User can like discussions and comments.
5. User can search for posts using hashtags, and for users based on name.
6. User can follow/unfollow other users.

## Setup Instructions

### Prerequisites

- Docker
- Docker Compose

### Steps

1. Clone the repository:
    ```
    git clone https://github.com/ekiwaka/the-social-network.git
    ```

2. Build and start the services using Docker Compose:
    ```
    docker-compose up --build
    ```

3. Create tables in MySQL instance
    ```
    CREATE TABLE users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        mobile_no VARCHAR(15) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    CREATE TABLE follows (
        id INT AUTO_INCREMENT PRIMARY KEY,
        follower_id INT NOT NULL,
        followee_id INT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        FOREIGN KEY (follower_id) REFERENCES users(id),
        FOREIGN KEY (followee_id) REFERENCES users(id)
    );


    CREATE TABLE discussions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        text TEXT NOT NULL,
        image VARCHAR(255),
        hashtags VARCHAR(255),
        user_id INT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE comments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        text TEXT NOT NULL,
        discussion_id INT NOT NULL,
        user_id INT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        FOREIGN KEY (discussion_id) REFERENCES discussions(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE target_entities (
        id INT AUTO_INCREMENT PRIMARY KEY,
        entity_type ENUM('discussion', 'comment') NOT NULL,
        entity_id INT NOT NULL,
        UNIQUE KEY (entity_type, entity_id)
    );

    CREATE TABLE likes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        target_entity_id INT NOT NULL,
        user_id INT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        FOREIGN KEY (target_entity_id) REFERENCES target_entities(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    ```
    
4. The services will be available at the following URLs:
    - API Gateway: `http://localhost:5000`
    - User Service: `http://localhost:5001`
    - Discussion Service: `http://localhost:5002`
    - Comment Service: `http://localhost:5003`
    - Like Service: `http://localhost:5004`
    - Search Service: `http://localhost:5005`

### Environment Variables

Each service requires the following environment variables:

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `SECRET_KEY`
- `ELASTICSEARCH_URL`
- `ELASTICSEARCH_SSL_VERIFY`: This is to use ElasticSearch without API keys

## API Documentation

The API Gateway is responsible for routing the request to the correct service

### User Service Endpoints

- **Create User**: `POST /users`
- **Login Users**: `POST /login`
- **Update User**: `PUT /users/<user_id>`
- **Delete User**: `DELETE /users/<user_id>`
- **Follow User**: `POST /users/<user_id>/follow`
- **Unfollow User**: `POST /users/<user_id>/unfollow`
- **List All Users**: `GET /users`
- **List All Users That Current User Follows**: `GET /users/following`
- **List All Users Follow Current User**: `GET /users/followers`

### Discussion Service Endpoints

- **Create Discussion**: `POST /discussions`
- **Update Discussion**: `PUT /discussions/<discussion_id>`
- **Delete Discussion**: `DELETE /discussions/<discussion_id>`
- **List All Discussions Of Current User**: `GET /discussions`

### Comment Service Endpoints

- **Create Comment**: `POST /comments`
- **Update Comment**: `PUT /comments/<comment_id>`
- **Delete Comment**: `DELETE /comments/<comment_id>`
- **List All Comments Of Current User**: `GET /comments`

### Like Service Endpoints

- **Create Like**: `POST /likes`
- **Delete Like**: `DELETE /likes/<like_id>`
- **List All Likes Of Current User**: `GET /likes`

### Search Service Endpoint

- **Search All Users**: `GET /search/users?query=<name>`
- **Search All Users**: `GET /search/discussions_by_text?text=<text>`
- **Search All Users**: `GET /search/discussions_by_hashtag?hashtag=<hashtag>`


## License

This project is licensed under the MIT License.