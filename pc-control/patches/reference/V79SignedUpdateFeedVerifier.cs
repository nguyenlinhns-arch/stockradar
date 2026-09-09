// REVIEW/REFERENCE ONLY. Integrate through the V7.9 self-maintenance pipeline.
// No network access, package download, pointer switch, or process execution occurs here.
// Target runtime: .NET 10 Windows.

using System.Buffers;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace ThayLinh.PcControl.UpdateReference;

internal sealed record VerifiedUpdateFeed(
    string Channel,
    string Version,
    string ReleaseId,
    int ReleaseEpoch,
    DateTimeOffset PublishedAt,
    DateTimeOffset ExpiresAt,
    string MinManagerVersion,
    string MinSafeVersion,
    string Asset,
    long PackageSize,
    string PackageSha256,
    int HealthTimeoutSeconds,
    int RequiredAgentCount,
    int RequiredRelayCount,
    byte[] CanonicalSignedBytes,
    byte[] EnvelopeSha256);

internal static partial class V79SignedUpdateFeedVerifier
{
    internal const string Schema = "thaylinh.pc.update-feed.v2";
    internal const int MaxEnvelopeBytes = 100_000;
    internal const long MaxPackageBytes = 700_000_000;
    internal const int P1363SignatureBytes = 64;

    // Tight, implementation-owned grammar. Do not silently broaden from a remote feed.
    [GeneratedRegex(@"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$", RegexOptions.CultureInvariant)]
    private static partial Regex SemVerRegex();

    [GeneratedRegex(@"^[0-9A-Za-z._-]+$", RegexOptions.CultureInvariant)]
    private static partial Regex ReleaseIdRegex();

    [GeneratedRegex(@"^[0-9A-Za-z._-]+\.zip$", RegexOptions.CultureInvariant)]
    private static partial Regex AssetRegex();

    [GeneratedRegex(@"^[0-9a-f]{64}$", RegexOptions.CultureInvariant)]
    private static partial Regex Sha256Regex();

    [GeneratedRegex(@"^[a-z0-9][a-z0-9._-]{0,63}$", RegexOptions.CultureInvariant)]
    private static partial Regex KeyIdRegex();

    internal static VerifiedUpdateFeed Verify(
        ReadOnlySpan<byte> envelopeUtf8,
        string expectedKeyId,
        ReadOnlySpan<byte> publisherPublicKeyPemUtf8,
        DateTimeOffset nowUtc,
        TimeSpan maxFutureSkew,
        TimeSpan maxEnvelopeLifetime)
    {
        if (envelopeUtf8.Length is <= 0 or > MaxEnvelopeBytes)
            throw new InvalidDataException("UPDATE_ENVELOPE_SIZE_INVALID");
        if (!KeyIdRegex().IsMatch(expectedKeyId))
            throw new InvalidDataException("UPDATE_EXPECTED_KEY_ID_INVALID");
        if (maxFutureSkew < TimeSpan.Zero || maxFutureSkew > TimeSpan.FromHours(1))
            throw new ArgumentOutOfRangeException(nameof(maxFutureSkew));
        if (maxEnvelopeLifetime <= TimeSpan.Zero || maxEnvelopeLifetime > TimeSpan.FromDays(31))
            throw new ArgumentOutOfRangeException(nameof(maxEnvelopeLifetime));

        var options = new JsonDocumentOptions
        {
            AllowTrailingCommas = false,
            CommentHandling = JsonCommentHandling.Disallow,
            MaxDepth = 16
        };

        using var doc = JsonDocument.Parse(envelopeUtf8, options);
        var root = doc.RootElement;
        RequireObject(root, "envelope");
        RejectDuplicatePropertiesRecursively(root, "envelope");
        RequireExactPropertySet(root, "envelope", "schema", "key_id", "signed", "signature");

        var schema = RequireString(root, "schema");
        if (!StringComparer.Ordinal.Equals(schema, Schema))
            throw new InvalidDataException("UPDATE_SCHEMA_UNSUPPORTED");

        var keyId = RequireString(root, "key_id");
        if (!KeyIdRegex().IsMatch(keyId) || !StringComparer.Ordinal.Equals(keyId, expectedKeyId))
            throw new InvalidDataException("UPDATE_KEY_ID_MISMATCH");

        var signed = RequireProperty(root, "signed");
        RequireObject(signed, "signed");
        ValidateAsciiTree(signed, "signed");
        RejectFloatingPointNumbers(signed, "signed");

        var canonical = Canonicalize(signed);
        var signatureText = RequireString(root, "signature");
        byte[] signature;
        try
        {
            signature = Convert.FromBase64String(signatureText);
        }
        catch (FormatException ex)
        {
            throw new InvalidDataException("UPDATE_SIGNATURE_BASE64_INVALID", ex);
        }
        if (signature.Length != P1363SignatureBytes)
            throw new InvalidDataException("UPDATE_SIGNATURE_LENGTH_INVALID");

        using var ecdsa = ECDsa.Create();
        try
        {
            ecdsa.ImportFromPem(Encoding.ASCII.GetString(publisherPublicKeyPemUtf8));
        }
        catch (Exception ex) when (ex is ArgumentException or CryptographicException)
        {
            throw new InvalidDataException("UPDATE_PUBLISHER_KEY_INVALID", ex);
        }

        var parameters = ecdsa.ExportParameters(includePrivateParameters: false);
        if (parameters.Q.X is null || parameters.Q.Y is null || parameters.Q.X.Length != 32 || parameters.Q.Y.Length != 32)
            throw new InvalidDataException("UPDATE_PUBLISHER_KEY_NOT_P256");

        var signatureOk = ecdsa.VerifyData(
            canonical,
            signature,
            HashAlgorithmName.SHA256,
            DSASignatureFormat.IeeeP1363FixedFieldConcatenation);
        CryptographicOperations.ZeroMemory(signature);
        if (!signatureOk)
            throw new InvalidDataException("UPDATE_SIGNATURE_INVALID");

        // Only after signature verification do signed values become trust inputs.
        return ValidateSignedFeed(
            signed,
            canonical,
            SHA256.HashData(envelopeUtf8),
            nowUtc.ToUniversalTime(),
            maxFutureSkew,
            maxEnvelopeLifetime);
    }

    private static VerifiedUpdateFeed ValidateSignedFeed(
        JsonElement signed,
        byte[] canonical,
        byte[] envelopeSha,
        DateTimeOffset nowUtc,
        TimeSpan maxFutureSkew,
        TimeSpan maxEnvelopeLifetime)
    {
        RequireExactPropertySet(
            signed,
            "signed",
            "channel", "version", "release_id", "release_epoch",
            "published_at", "expires_at", "min_manager_version", "min_safe_version",
            "package", "health");

        var channel = RequireString(signed, "channel");
        if (channel is not ("preview" or "stable"))
            throw new InvalidDataException("UPDATE_CHANNEL_INVALID");

        var version = RequireString(signed, "version");
        var minManagerVersion = RequireString(signed, "min_manager_version");
        var minSafeVersion = RequireString(signed, "min_safe_version");
        if (!SemVerRegex().IsMatch(version) ||
            !SemVerRegex().IsMatch(minManagerVersion) ||
            !SemVerRegex().IsMatch(minSafeVersion))
            throw new InvalidDataException("UPDATE_VERSION_INVALID");

        var releaseId = RequireString(signed, "release_id");
        if (releaseId.Length > 96 || !ReleaseIdRegex().IsMatch(releaseId))
            throw new InvalidDataException("UPDATE_RELEASE_ID_INVALID");

        var releaseEpoch = RequireInt32(signed, "release_epoch");
        if (releaseEpoch <= 0)
            throw new InvalidDataException("UPDATE_RELEASE_EPOCH_INVALID");

        var publishedAt = ParseCanonicalUtcTimestamp(RequireString(signed, "published_at"), "UPDATE_PUBLISHED_AT_INVALID");
        var expiresAt = ParseCanonicalUtcTimestamp(RequireString(signed, "expires_at"), "UPDATE_EXPIRES_AT_INVALID");
        if (publishedAt > nowUtc + maxFutureSkew)
            throw new InvalidDataException("UPDATE_PUBLISHED_IN_FUTURE");
        if (expiresAt <= nowUtc)
            throw new InvalidDataException("UPDATE_ENVELOPE_EXPIRED");
        if (expiresAt <= publishedAt || expiresAt - publishedAt > maxEnvelopeLifetime)
            throw new InvalidDataException("UPDATE_ENVELOPE_LIFETIME_INVALID");

        var package = RequireProperty(signed, "package");
        RequireObject(package, "package");
        RequireExactPropertySet(package, "package", "asset", "size", "sha256");
        var asset = RequireString(package, "asset");
        if (asset.Length > 160 || !AssetRegex().IsMatch(asset))
            throw new InvalidDataException("UPDATE_ASSET_INVALID");
        var packageSize = RequireInt64(package, "size");
        if (packageSize is <= 0 or > MaxPackageBytes)
            throw new InvalidDataException("UPDATE_PACKAGE_SIZE_INVALID");
        var packageSha = RequireString(package, "sha256");
        if (!Sha256Regex().IsMatch(packageSha))
            throw new InvalidDataException("UPDATE_PACKAGE_SHA256_INVALID");

        var health = RequireProperty(signed, "health");
        RequireObject(health, "health");
        RequireExactPropertySet(health, "health", "timeout_seconds", "required_agent_count", "required_relay_count");
        var timeout = RequireInt32(health, "timeout_seconds");
        var agentCount = RequireInt32(health, "required_agent_count");
        var relayCount = RequireInt32(health, "required_relay_count");
        if (timeout is < 30 or > 300 || agentCount != 1 || relayCount is < 0 or > 1)
            throw new InvalidDataException("UPDATE_HEALTH_POLICY_INVALID");

        return new VerifiedUpdateFeed(
            channel, version, releaseId, releaseEpoch, publishedAt, expiresAt,
            minManagerVersion, minSafeVersion, asset, packageSize, packageSha,
            timeout, agentCount, relayCount, canonical, envelopeSha);
    }

    internal static byte[] Canonicalize(JsonElement value)
    {
        var buffer = new ArrayBufferWriter<byte>();
        using (var writer = new Utf8JsonWriter(buffer, new JsonWriterOptions
        {
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
            Indented = false,
            SkipValidation = false
        }))
        {
            WriteCanonical(writer, value);
        }
        return buffer.WrittenSpan.ToArray();
    }

    private static void WriteCanonical(Utf8JsonWriter writer, JsonElement value)
    {
        switch (value.ValueKind)
        {
            case JsonValueKind.Object:
                writer.WriteStartObject();
                foreach (var property in value.EnumerateObject().OrderBy(p => p.Name, StringComparer.Ordinal))
                {
                    writer.WritePropertyName(property.Name);
                    WriteCanonical(writer, property.Value);
                }
                writer.WriteEndObject();
                break;
            case JsonValueKind.Array:
                // Feed v2 currently has no arrays, but canonical handling is deterministic.
                writer.WriteStartArray();
                foreach (var item in value.EnumerateArray())
                    WriteCanonical(writer, item);
                writer.WriteEndArray();
                break;
            case JsonValueKind.String:
                writer.WriteStringValue(value.GetString());
                break;
            case JsonValueKind.Number:
                if (!value.TryGetInt64(out var integer))
                    throw new InvalidDataException("UPDATE_SIGNED_FLOAT_FORBIDDEN");
                writer.WriteNumberValue(integer);
                break;
            case JsonValueKind.True:
                writer.WriteBooleanValue(true);
                break;
            case JsonValueKind.False:
                writer.WriteBooleanValue(false);
                break;
            case JsonValueKind.Null:
                writer.WriteNullValue();
                break;
            default:
                throw new InvalidDataException("UPDATE_JSON_KIND_INVALID");
        }
    }

    private static void RejectDuplicatePropertiesRecursively(JsonElement value, string path)
    {
        if (value.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in value.EnumerateObject())
            {
                if (!names.Add(property.Name))
                    throw new InvalidDataException($"UPDATE_DUPLICATE_PROPERTY:{path}.{property.Name}");
                RejectDuplicatePropertiesRecursively(property.Value, $"{path}.{property.Name}");
            }
        }
        else if (value.ValueKind == JsonValueKind.Array)
        {
            var index = 0;
            foreach (var item in value.EnumerateArray())
                RejectDuplicatePropertiesRecursively(item, $"{path}[{index++}]");
        }
    }

    private static void ValidateAsciiTree(JsonElement value, string path)
    {
        if (value.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in value.EnumerateObject())
            {
                RequireAscii(property.Name, $"{path}.<key>");
                ValidateAsciiTree(property.Value, $"{path}.{property.Name}");
            }
        }
        else if (value.ValueKind == JsonValueKind.Array)
        {
            var index = 0;
            foreach (var item in value.EnumerateArray())
                ValidateAsciiTree(item, $"{path}[{index++}]");
        }
        else if (value.ValueKind == JsonValueKind.String)
        {
            RequireAscii(value.GetString() ?? string.Empty, path);
        }
    }

    private static void RejectFloatingPointNumbers(JsonElement value, string path)
    {
        if (value.ValueKind == JsonValueKind.Number && !value.TryGetInt64(out _))
            throw new InvalidDataException($"UPDATE_SIGNED_FLOAT_FORBIDDEN:{path}");
        if (value.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in value.EnumerateObject())
                RejectFloatingPointNumbers(property.Value, $"{path}.{property.Name}");
        }
        else if (value.ValueKind == JsonValueKind.Array)
        {
            var index = 0;
            foreach (var item in value.EnumerateArray())
                RejectFloatingPointNumbers(item, $"{path}[{index++}]");
        }
    }

    private static void RequireAscii(string value, string path)
    {
        foreach (var ch in value)
            if (ch > 0x7F)
                throw new InvalidDataException($"UPDATE_NON_ASCII_SIGNED_VALUE:{path}");
    }

    private static DateTimeOffset ParseCanonicalUtcTimestamp(string value, string error)
    {
        if (!DateTimeOffset.TryParseExact(
                value,
                "yyyy-MM-dd'T'HH:mm:ss'Z'",
                CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out var parsed))
            throw new InvalidDataException(error);
        return parsed;
    }

    private static JsonElement RequireProperty(JsonElement obj, string name)
    {
        if (!obj.TryGetProperty(name, out var value))
            throw new InvalidDataException($"UPDATE_PROPERTY_REQUIRED:{name}");
        return value;
    }

    private static string RequireString(JsonElement obj, string name)
    {
        var value = RequireProperty(obj, name);
        if (value.ValueKind != JsonValueKind.String)
            throw new InvalidDataException($"UPDATE_STRING_REQUIRED:{name}");
        return value.GetString() ?? throw new InvalidDataException($"UPDATE_STRING_REQUIRED:{name}");
    }

    private static int RequireInt32(JsonElement obj, string name)
    {
        var value = RequireProperty(obj, name);
        if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt32(out var parsed))
            throw new InvalidDataException($"UPDATE_INT32_REQUIRED:{name}");
        return parsed;
    }

    private static long RequireInt64(JsonElement obj, string name)
    {
        var value = RequireProperty(obj, name);
        if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt64(out var parsed))
            throw new InvalidDataException($"UPDATE_INT64_REQUIRED:{name}");
        return parsed;
    }

    private static void RequireObject(JsonElement value, string name)
    {
        if (value.ValueKind != JsonValueKind.Object)
            throw new InvalidDataException($"UPDATE_OBJECT_REQUIRED:{name}");
    }

    private static void RequireExactPropertySet(JsonElement obj, string path, params string[] expected)
    {
        var actual = obj.EnumerateObject().Select(p => p.Name).ToHashSet(StringComparer.Ordinal);
        var required = expected.ToHashSet(StringComparer.Ordinal);
        if (!actual.SetEquals(required))
            throw new InvalidDataException($"UPDATE_PROPERTY_SET_INVALID:{path}");
    }
}
