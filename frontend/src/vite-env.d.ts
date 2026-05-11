/// <reference types="vite/client" />

declare module "cytoscape-fcose" {
  import type cytoscape from "cytoscape";
  const ext: cytoscape.Ext;
  export default ext;
}