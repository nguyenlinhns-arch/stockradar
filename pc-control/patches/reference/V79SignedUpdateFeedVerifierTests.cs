// REVIEW/REFERENCE ONLY. Adapt namespace/test framework to the existing V7.9 test project.
// This intentionally contains no production private signing material.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ThayLinh.PcControl.UpdateReference.Tests;

internal static class V79SignedUpdateFeedVerifierTestMatrix
{
    internal const string FixtureCanonicalSha256 = "1b3f1d908936c627c7b902d22ca4d67d1fd3b905946c1316d08deb9f3063f8fe";
    internal const string FixtureKeyId = "fixture-p256-01";

    // Wire these cases into the repository's existing test framework. Each case is a hard acceptance gate.
    internal static readonly string[] RequiredCases =
    [
        "fixture_signature_verifies",
        "fixture_canonical_sha256_matches",
        "json_whitespace_and_property_reordering_preserve_verification",
        "any_signed_field_mutation_fails_signature",
        "wrong_key_id_fails",
        "wrong_public_key_fails",
        "non_p256_key_fails",
        "malformed_base64_fails",
        "signature_not_64_byte_p1363_fails",
        "duplicate_root_property_fails",
        "duplicate_nested_property_fails",
        "unknown_root_property_fails_closed",
        "unknown_signed_property_fails_closed",
        "floating_point_signed_number_fails",
        "non_ascii_signed_string_fails",
        "release_id_dot_fails",
        "release_id_dotdot_fails",
        "release_id_path_separator_fails",
        "asset_path_separator_fails",
        "asset_windows_con_zip_fails",
        "asset_windows_nul_zip_fails",
        "package_size_zero_fails",
        "package_size_over_700mb_fails",
        "sha256_uppercase_or_wrong_length_fails",
        "timestamp_noncanonical_offset_fails",
        "published_too_far_in_future_fails",
        "expired_envelope_fails",
        "envelope_lifetime_over_policy_fails",
        "health_timeout_out_of_range_fails",
        "agent_count_not_one_fails",
        "relay_count_over_one_fails",
        "envelope_over_100kb_fails_before_parse",
        "lower_release_epoch_is_rejected_by_security_state",
        "same_release_id_different_hash_is_security_error",
        "same_release_identity_is_idempotent",
        "channel_mismatch_with_local_setting_fails",
        "automatic_semver_downgrade_fails",
    ];

    internal static byte[] CanonicalSignedBytesFromEnvelope(byte[] envelope)
    {
        using var doc = JsonDocument.Parse(envelope);
        var signed = doc.RootElement.GetProperty("signed");
        return V79SignedUpdateFeedVerifier.Canonicalize(signed);
    }

    internal static string Sha256Hex(ReadOnlySpan<byte> data) => Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();

    internal static void AssertFixtureCanonicalHash(byte[] envelope)
    {
        var canonical = CanonicalSignedBytesFromEnvelope(envelope);
        if (!string.Equals(Sha256Hex(canonical), FixtureCanonicalSha256, StringComparison.Ordinal))
            throw new InvalidOperationException("fixture canonicalization drifted");
    }

    internal static byte[] ReformatEnvelopeWithoutChangingSignedValues(byte[] envelope)
    {
        using var doc = JsonDocument.Parse(envelope);
        // Reformatting the envelope must not affect signature verification because only canonicalized `signed` is verified.
        return JsonSerializer.SerializeToUtf8Bytes(doc.RootElement, new JsonSerializerOptions { WriteIndented = false });
    }

    internal static byte[] ReplaceAsciiOnce(byte[] input, string from, string to)
    {
        if (from.Length != to.Length)
            throw new ArgumentException("mutation helper requires same-length replacement");
        var text = Encoding.UTF8.GetString(input);
        var index = text.IndexOf(from, StringComparison.Ordinal);
        if (index < 0) throw new InvalidOperationException("fixture mutation token not found");
        text = text[..index] + to + text[(index + from.Length)..];
        return Encoding.UTF8.GetBytes(text);
    }
}
