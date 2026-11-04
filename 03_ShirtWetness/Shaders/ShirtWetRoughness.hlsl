// Wet cotton stays fairly rough: fibres still poke out of the water. Only saturated fabric
// pools a thin film in folds, which gives broken, small highlights rather than satin sheen.
float w = saturate(WF.x);
float fibre = WF.y;
float r = lerp(DryRoughness, WetRoughness + (fibre-0.5)*0.12, smoothstep(0.0, 0.8, w));
float film = FilmAmount * smoothstep(0.85, 1.0, w) * saturate(fibre*2.0 - 0.6);
return saturate(lerp(r, FilmRoughness, film));
