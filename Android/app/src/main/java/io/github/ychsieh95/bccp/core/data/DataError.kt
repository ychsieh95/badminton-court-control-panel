package io.github.ychsieh95.bccp.core.data

import io.github.ychsieh95.bccp.core.network.ErrorEnvelope
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import java.io.IOException

sealed class DataError(message: String, cause: Throwable? = null) : Exception(message, cause) {
    class Network(cause: Throwable) : DataError("Network error", cause)

    /** Server rejected the request. [message] is already localized by the server. */
    class Api(
        val status: Int,
        val code: String,
        message: String,
        val fields: Map<String, String> = emptyMap(),
    ) : DataError(message)

    class Unexpected(cause: Throwable) : DataError(cause.message ?: "Unexpected error", cause)
}

internal suspend fun <T> apiCall(json: Json, block: suspend () -> T): Result<T> = try {
    Result.success(block())
} catch (e: CancellationException) {
    throw e
} catch (e: HttpException) {
    Result.failure(e.toDataError(json))
} catch (e: IOException) {
    Result.failure(DataError.Network(e))
} catch (e: Exception) {
    Result.failure(DataError.Unexpected(e))
}

/** For `204 No Content` endpoints, where Retrofit hands back the raw response. */
internal fun retrofit2.Response<Unit>.requireSuccess() {
    if (!isSuccessful) throw HttpException(this)
}

private fun HttpException.toDataError(json: Json): DataError {
    val raw = response()?.errorBody()?.string().orEmpty()
    val body = runCatching { json.decodeFromString(ErrorEnvelope.serializer(), raw).error }.getOrNull()
    return DataError.Api(
        status = code(),
        code = body?.code ?: "http_${code()}",
        message = body?.message?.takeIf { it.isNotBlank() } ?: message(),
        fields = body?.fields.orEmpty(),
    )
}
