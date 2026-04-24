"""Node name constants for the carousel pipeline phases.

Centralised so every phase module can reference node names without
circular imports.
"""

NODE_RESEARCH = "research"
NODE_CONTENT = "content"
NODE_PERSIST_SLIDES = "persist_slides"
NODE_DESIGN = "design"
NODE_IMAGES_DISPATCH = "images_dispatch"
NODE_IMAGE_WORKER = "image_worker"
NODE_IMAGES_COLLECT = "images_collect"
NODE_EXPORT = "export"
NODE_CAPTION = "caption"
NODE_LINKEDIN = "linkedin"
NODE_FINALIZE = "finalize"
