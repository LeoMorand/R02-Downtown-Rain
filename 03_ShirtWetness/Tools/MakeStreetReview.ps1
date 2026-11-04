# Dry vs rain-soaked board for the R02 street showcase. Unretouched PIE captures, resize only.
# Soaked = look_review.soak(30): 30 s of the wetness simulation under the level's manual rain.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$shots='D:/aco/unreal/Stormfall/Saved/Screenshots'
$out='D:/aco/unreal/Stormfall/Preview/ShirtWetness/street_showcase.png'
$cells=@(@{File='street_dry_v4.png';Tag='DRY  /  rain just started'},@{File='street_soak30_v4.png';Tag='30 s IN RAIN  /  simulated wetness 0.88'})
$w=960;$h=543;$pad=12;$head=40
$canvas=[System.Drawing.Bitmap]::new($pad*3+$w*2,$pad*2+$head+$h+36)
$g=[System.Drawing.Graphics]::FromImage($canvas)
$font=[System.Drawing.Font]::new('Segoe UI',20,[System.Drawing.FontStyle]::Regular,[System.Drawing.GraphicsUnit]::Pixel)
$small=[System.Drawing.Font]::new('Segoe UI',16,[System.Drawing.FontStyle]::Regular,[System.Drawing.GraphicsUnit]::Pixel)
$fg=[System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#e5edf6'))
$dim=[System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#9cabb8'))
try {
    $g.Clear([System.Drawing.ColorTranslator]::FromHtml('#141a20'))
    $g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    for($c=0;$c -lt 2;$c++) {
        $x=$pad+$c*($w+$pad)
        $g.DrawString($cells[$c].Tag,$font,$fg,[single]$x,[single]($pad+6))
        $img=[System.Drawing.Image]::FromFile((Join-Path $shots $cells[$c].File))
        try { $g.DrawImage($img,[System.Drawing.Rectangle]::new($x,$pad+$head,$w,$h)) } finally { $img.Dispose() }
    }
    $g.DrawString('L_ShirtWetness_Street (copy of R02 Downtown Rain) | same camera and light (key 70 cd, rim 250 cd), close rain emitter, idle animation | weather from MPC_RoadWeather',$small,$dim,[single]$pad,[single]($canvas.Height-30))
    $canvas.Save($out,[System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output $out
} finally { $g.Dispose();$canvas.Dispose();$font.Dispose();$small.Dispose();$fg.Dispose();$dim.Dispose() }
