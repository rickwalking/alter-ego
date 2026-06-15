"""Infrastructure layer for the editorial bounded context.

Private to the module. The concrete carousel persistence adapter is NOT
relocated in AE-0108 (behavior-preserving scaffolding); it remains at its legacy
location and is supplied to the module's ``bootstrap_module`` by the inbound edge
as the re-exported ``CarouselRepository`` port. Adapter relocation is a later
phase (AE-0109/0110).
"""
