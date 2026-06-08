/**
 * Global app settings.
 */
 var AppSettings = {};
 
 /**
 * API urls
 */
 AppSettings.APIServer = {
  baseAddress: "{{SERVER_WEB_ADDRESS}}{{BACKEND_ADDITIONAL_PORT}}/api/",
 }
 import createUrls from "./AppUrls.js";
 AppSettings.APIServer = createUrls(AppSettings.APIServer.baseAddress);

 export default AppSettings;