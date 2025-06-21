/**
 * Global app settings.
 */
 var AppSettings = {};

 /**
 * General settings for the app.
 */
 AppSettings.General = {
  contactEmail: "{{CONTACT_EMAIL}}",
  appName: "{{APP_NAME}}",
  timezone: "{{TIMEZONE}}",
 }
 
 AppSettings.Login = {
  loginText: "Login with your credentials.",
  usernameField: "Username",
  passwordField: "Password"
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