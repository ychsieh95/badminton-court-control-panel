package io.github.ychsieh95.bccp.core.network

import io.github.ychsieh95.bccp.core.model.Meta
import kotlinx.serialization.json.JsonObject
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.HTTP
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.QueryMap

/** `/api/v1` — see Web/API.md. Endpoints answering `204` return `Response<Unit>`. */
interface BccpApi {
    @GET("meta") suspend fun meta(): Meta

    @GET("courts") suspend fun courts(@QueryMap filters: Map<String, String>): CourtListResponse
    @GET("courts/{guid}") suspend fun court(@Path("guid") guid: String): CourtResponse
    @POST("courts/{guid}/join") suspend fun join(@Path("guid") guid: String, @Body body: JsonObject): CourtResponse
    @POST("courts/{guid}/leave") suspend fun leave(@Path("guid") guid: String, @Body body: JsonObject): CourtResponse
    @POST("contact") suspend fun contact(@Body body: JsonObject): JsonObject

    @POST("courts/{guid}/push/status") suspend fun pushStatus(@Path("guid") guid: String, @Body body: JsonObject): PushStatusResponse
    @PUT("courts/{guid}/push") suspend fun subscribePush(@Path("guid") guid: String, @Body body: JsonObject): PushStatusResponse
    @HTTP(method = "DELETE", path = "courts/{guid}/push", hasBody = true)
    suspend fun unsubscribePush(@Path("guid") guid: String, @Body body: JsonObject): PushStatusResponse
    @PUT("push/token") suspend fun replacePushToken(@Body body: JsonObject): JsonObject
    @PUT("me/push-token") suspend fun registerAccountPushToken(@Body body: JsonObject): JsonObject

    @POST("auth/signup") suspend fun signup(@Body body: JsonObject): AuthResponse
    @POST("auth/login") suspend fun login(@Body body: JsonObject): AuthResponse
    @POST("auth/logout") suspend fun logout(): Response<Unit>
    @GET("auth/tokens") suspend fun tokens(): TokensResponse
    @DELETE("auth/tokens/{id}") suspend fun revokeToken(@Path("id") id: Int): Response<Unit>

    @GET("me") suspend fun me(): UserResponse
    @PATCH("me") suspend fun updateMe(@Body body: JsonObject): UserResponse
    @POST("me/password") suspend fun changePassword(@Body body: JsonObject): UserResponse
    @Multipart @PUT("me/avatar") suspend fun uploadAvatar(@Part avatar: MultipartBody.Part): UserResponse
    @DELETE("me/avatar") suspend fun deleteAvatar(): UserResponse
    @GET("me/saved-locations") suspend fun savedLocations(): SavedLocationsResponse
    @DELETE("me/saved-locations/{id}") suspend fun deleteSavedLocation(@Path("id") id: Int): Response<Unit>
    @HTTP(method = "DELETE", path = "me", hasBody = true) suspend fun deleteAccount(@Body body: JsonObject): Response<Unit>
    @GET("me/courts") suspend fun myCourts(@Query("limit") limit: Int, @Query("offset") offset: Int): CourtListResponse

    @POST("courts") suspend fun createCourt(@Body body: JsonObject): CourtResponse
    @Multipart @POST("courts") suspend fun createCourt(@Part("court") court: RequestBody, @Part media: List<MultipartBody.Part>): CourtResponse
    @PATCH("courts/{guid}") suspend fun updateCourt(@Path("guid") guid: String, @Body body: JsonObject): CourtResponse
    @Multipart @PATCH("courts/{guid}") suspend fun updateCourt(
        @Path("guid") guid: String,
        @Part("court") court: RequestBody,
        @Part media: List<MultipartBody.Part>,
    ): CourtResponse
    @DELETE("courts/{guid}") suspend fun deleteCourt(@Path("guid") guid: String): Response<Unit>
    @POST("courts/{guid}/archive") suspend fun archiveCourt(@Path("guid") guid: String): CourtResponse
    @POST("courts/{guid}/restore") suspend fun restoreCourt(@Path("guid") guid: String): CourtResponse
    @POST("courts/{guid}/roll-clearing") suspend fun startRollClearing(@Path("guid") guid: String): CourtResponse
    @PATCH("courts/{guid}/roll-clearing") suspend fun updateRollClearing(@Path("guid") guid: String, @Body body: JsonObject): CourtResponse
    @DELETE("courts/{guid}/roll-clearing") suspend fun endRollClearing(@Path("guid") guid: String): CourtResponse
    @PATCH("courts/{guid}/participants/{id}") suspend fun updateParticipant(
        @Path("guid") guid: String,
        @Path("id") id: Int,
        @Body body: JsonObject,
    ): CourtResponse
    @DELETE("courts/{guid}/participants/{id}") suspend fun deleteParticipant(@Path("guid") guid: String, @Path("id") id: Int): CourtResponse

    @GET("admin/courts") suspend fun adminCourts(@QueryMap filters: Map<String, String>): CourtListResponse
    @GET("admin/users") suspend fun adminUsers(): AdminUsersResponse
    @POST("admin/users/{id}/{action}") suspend fun adminUserAction(@Path("id") id: Int, @Path("action") action: String): AdminUserResponse
    @POST("admin/users/{id}/temporary-password") suspend fun adminTemporaryPassword(@Path("id") id: Int, @Body body: JsonObject): AdminUserResponse
    @PUT("admin/users/{id}/role") suspend fun adminSetRole(@Path("id") id: Int, @Body body: JsonObject): AdminUserResponse
    @DELETE("admin/users/{id}") suspend fun adminDeleteUser(@Path("id") id: Int): Response<Unit>
    @GET("admin/messages") suspend fun adminMessages(@Query("status") status: String, @Query("page") page: Int): MessagesResponse
    @PATCH("admin/messages/{id}") suspend fun adminUpdateMessage(@Path("id") id: Int, @Body body: JsonObject): MessageResponse
    @GET("admin/settings") suspend fun adminSettings(): SettingsResponse
    @PATCH("admin/settings") suspend fun adminUpdateSettings(@Body body: JsonObject): SettingsResponse
}
