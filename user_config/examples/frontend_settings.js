/**
 * Global app settings.
 */
 var AppSettings = {};

 /**
 * General settings for the app.
 */
 AppSettings.General = {
    // Edit in settings file, overridden by 'start-main-server' make task.
  contactEmail: "support@youremaildomain.com",
   // Edit in settings file, overridden by 'start-main-server' make task.
  appName: "Containers on the fly",
   // Edit in settings file, overridden by 'start-main-server' make task.
  timezone: "Europe/Helsinki",
 }
 
 AppSettings.Login = {
  // Text visible in the login screen in the web interface
  loginText: "Login with your credentials.",
  // Username field help label in the login screen in the web interface
  usernameField: "Username",
  // Password field help label in the login screen in the web interface
  passwordField: "Password"
 }
 
 /**
 * API urls
 */
 AppSettings.APIServer = {
    // Edit in settings file, overridden by 'start-main-server' make task.
  baseAddress: "http://localhost:8000/api/",
 }
 const createUrls = require("./AppUrls.js");
 AppSettings.APIServer = createUrls(AppSettings.APIServer.baseAddress);
 
 export default AppSettings;