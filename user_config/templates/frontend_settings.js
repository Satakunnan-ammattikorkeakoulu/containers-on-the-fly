/**
 * Global app settings.
 */
 var AppSettings = {};

 /**
 * General settings for the app.
 */
 AppSettings.General = {
  appName: "{{APP_NAME}}",
 }
 
 /**
 * API urls
 */
 AppSettings.APIServer = {
  baseAddress: "{{SERVER_WEB_ADDRESS}}{{BACKEND_ADDITIONAL_PORT}}/api/",
 }
 const createUrls = require("./AppUrls.js");
 AppSettings.APIServer = createUrls(AppSettings.APIServer.baseAddress);
 
 export default AppSettings; 