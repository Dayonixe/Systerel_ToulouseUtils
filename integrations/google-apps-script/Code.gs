/**
 * Publie uniquement les lignes explicitement approuvées du Google Sheet.
 * Le script doit être attaché au classeur alimenté par Tally.
 */
const SHEET_NAME = "Soumissions";
const APPROVED_STATUSES = new Set(["approved", "approuve", "valide"]);

function normaliseHeader(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
}

function doGet() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = spreadsheet.getSheetByName(SHEET_NAME);
  if (!sheet) {
    return jsonResponse({ schemaVersion: 1, codes: [] });
  }

  const values = sheet.getDataRange().getDisplayValues();
  if (values.length < 2) {
    return jsonResponse({ schemaVersion: 1, codes: [] });
  }

  const headers = values[0].map(normaliseHeader);
  const column = (...names) => {
    for (const name of names.map(normaliseHeader)) {
      const index = headers.indexOf(name);
      if (index >= 0) return index;
    }
    return -1;
  };
  const offerIdColumn = column("offer_id");
  const codeColumn = column("code", "Code promotionnel reçu");
  const statusColumn = column("status");

  if (offerIdColumn < 0 || codeColumn < 0 || statusColumn < 0) {
    throw new Error(
      "Colonnes requises : offer_id, Code promotionnel reçu (ou code) et status"
    );
  }

  const codes = values.slice(1).flatMap((row) => {
    const status = normaliseHeader(row[statusColumn]);
    if (!APPROVED_STATUSES.has(status)) return [];

    return [{
      offerId: String(row[offerIdColumn] || "").trim(),
      code: String(row[codeColumn] || "").trim(),
      status: "approved",
    }];
  });

  return jsonResponse({ schemaVersion: 1, codes });
}

function jsonResponse(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}
