/** Analytics is not its own key — it ships inside the "alerts" tab, labelled
 *  "Alerts & Analytics". A dead "analytics" member used to live here; nothing
 *  rendered for it, so setting it produced a blank drawer. */
export type TabKey = "map" | "modules" | "fraud-rings" | "alerts" | "disrupt" | "metrics" | "research";
