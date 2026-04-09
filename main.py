{
  "openapi": "3.1.0",
  "info": {
    "title": "Reference Verifier API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://reference-verifier-api-production.up.railway.app"
    }
  ],
  "paths": {
    "/verify-batch": {
      "post": {
        "operationId": "verifyBatch",
        "summary": "Verify and format multiple references",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "references": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    }
                  }
                },
                "required": ["references"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Verification results",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "summary": {
                      "type": "object",
                      "properties": {
                        "verified": {
                          "type": "integer"
                        },
                        "not_found": {
                          "type": "integer"
                        }
                      }
                    },
                    "results": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "status": {
                            "type": "string"
                          },
                          "formatted": {
                            "type": "string"
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
