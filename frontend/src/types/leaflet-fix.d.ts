// Fix for leaflet types not resolving properly with verbatimModuleSyntax + bundler mode
// This ensures leaflet's types are available as module exports
declare module "leaflet" {
  export * from "@types/leaflet";
}
