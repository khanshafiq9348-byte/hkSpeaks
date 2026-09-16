# Security Model

1. **Authentication & Sessions**:
   - Password hashing via Bcrypt with salt.
   - JWT tokens signed with HMAC-SHA256.
2. **API Keys**:
   - Random 32-byte cryptographic entropy.
   - Hashed using SHA-256 before storage in database.
   - Full key displayed to the user only once upon creation.
3. **Audio File Security**:
   - Validated through FFmpeg inspection before storage.
   - Stored in private directory structure outside public web root.
   - Storage endpoints verify access rights before serving.
4. **Rate Limiting**:
   - Sliding-window rate limiting per IP / authorization token to prevent abuse.
5. **Ownership Isolation**:
   - Every protected route enforces server-side ownership checks (`user_id == current_user.id`). Client-supplied owner fields are ignored.
