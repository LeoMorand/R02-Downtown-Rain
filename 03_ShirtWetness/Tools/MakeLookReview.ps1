# Before/after board for the wet cotton look pass. Unretouched PIE captures, crop/resize only.
# Before = look_review.look(enabled=False) on the same MIDs (previous satin-era parameters).
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$shots='D:/aco/unreal/Stormfall/Saved/Screenshots'
$previewRoot='D:/aco/unreal/Stormfall/Preview/ShirtWetness'
$rows=@(
    @{Before='look_wet_before2.png';After='look_wet_after_v4.png';Label='SOAKED  /  original dark shirt  /  wetness 1.0'},
    @{Before='look_water_white_before.png';After='look_water_white_after_v2.png';Label='PARTLY IN WATER  /  near-white shirt check (PIE tint x6)'}
)
$cellW=760;$cellH=520;$pad=12;$head=44
$canvas=[System.Drawing.Bitmap]::new($pad*3+$cellW*2,$pad+($head+$cellH+$pad)*$rows.Count+40)
$g=[System.Drawing.Graphics]::FromImage($canvas)
$font=[System.Drawing.Font]::new('Segoe UI',22,[System.Drawing.FontStyle]::Regular,[System.Drawing.GraphicsUnit]::Pixel)
$small=[System.Drawing.Font]::new('Segoe UI',17,[System.Drawing.FontStyle]::Regular,[System.Drawing.GraphicsUnit]::Pixel)
$fg=[System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#e5edf6'))
$dim=[System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#9cabb8'))
try {
    $g.Clear([System.Drawing.ColorTranslator]::FromHtml('#141a20'))
    $g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    for($r=0;$r -lt $rows.Count;$r++) {
        $y=$pad+$r*($head+$cellH+$pad)
        $g.DrawString($rows[$r].Label,$font,$fg,[single]$pad,[single]($y+8))
        $cols=@(@{File=$rows[$r].Before;Tag='BEFORE'},@{File=$rows[$r].After;Tag='AFTER'})
        for($c=0;$c -lt 2;$c++) {
            $x=$pad+$c*($cellW+$pad)
            $img=[System.Drawing.Image]::FromFile((Join-Path $shots $cols[$c].File))
            try { $g.DrawImage($img,[System.Drawing.Rectangle]::new($x,$y+$head,$cellW,$cellH),260,0,760,520,[System.Drawing.GraphicsUnit]::Pixel) }
            finally { $img.Dispose() }
            $g.DrawString($cols[$c].Tag,$small,$fg,[single]($x+10),[single]($y+$head+8))
        }
    }
    $g.DrawString('UE 5.8 PIE captures, same actor / camera / light / wetness state; only wet-look parameters differ.',$small,$dim,[single]$pad,[single]($canvas.Height-32))
    $out=Join-Path $previewRoot 'look_comparison.png'
    $canvas.Save($out,[System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output $out
} finally { $g.Dispose();$canvas.Dispose();$font.Dispose();$small.Dispose();$fg.Dispose();$dim.Dispose() }
