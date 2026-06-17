const WebSocket = require("ws");

const esmRequire = require("esm")(module);
const LeapMotion = esmRequire("./LeapMotion.js");

LeapMotion.WebSocket = WebSocket;
LeapMotion.CustomEvent = class {
    constructor(type, options) {
        this.type = type;
        this.detail = options.detail;
    }
}

module.exports = LeapMotion;