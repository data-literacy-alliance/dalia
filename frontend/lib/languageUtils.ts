const languageNames = new Intl.DisplayNames(['en'], {
  type: 'language',
  languageDisplay: 'standard',
});

// Mapping of full language names to BCP 47 language codes
const languageNameMap: { [key: string]: string } = {
  English: 'en',
  German: 'de',
  // Add more mappings here for other languages
  // Example: "French": "fr", "Spanish": "es", etc.
};

export function getLanguageName(fullLanguageName: string) {
  if (fullLanguageName.length !== 2) {
    return fullLanguageName;
  }
  // Expect full language name as input
  // 1. Lookup BCP 47 code from full language name
  const shortLanguageName = languageNameMap[fullLanguageName];

  if (!shortLanguageName) {
    console.warn(
      'No BCP 47 code mapping found for language:',
      fullLanguageName
    );
    return 'NA'; // Return "NA" (not available) if no mapping is found
  }

  // 2. Basic BCP 47 language tag validation (keep this for safety)
  const languageCodeRegex =
    /^[a-z]{2,3}(?:-[A-Z]{2,3})?(?:-[a-zA-Z]{4})?(?:-[0-9]{3}|[a-zA-Z]{5,8})?(?:-(?:[0-9a-zA-Z]{1,8}))*$/;

  if (!languageCodeRegex.test(shortLanguageName)) {
    console.warn(
      'Invalid BCP 47 language code after mapping:',
      shortLanguageName,
      'Original name:',
      fullLanguageName
    );
    return 'NA'; // Return "NA" (not available) if mapped code is still invalid
  }

  // 3. Use Intl.DisplayNames with the *BCP 47 code*
  try {
    const name = languageNames.of(shortLanguageName);
    return name ? name.charAt(0).toUpperCase() + name.slice(1) : '';
  } catch (error) {
    console.error(
      'Error in getLanguageName for code:',
      shortLanguageName,
      'Original name:',
      fullLanguageName,
      error
    );
    return 'NA'; // Return "NA" (not available) if Intl.DisplayNames fails
  }
}
