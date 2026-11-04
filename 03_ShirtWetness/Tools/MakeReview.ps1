# Arrange unretouched UE captures. Only crop/resize for comparison layout.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$previewRoot='D:/aco/unreal/Stormfall/Preview/ShirtWetness'
$canvas=[System.Drawing.Bitmap]::new(1728,510)
$graphics=[System.Drawing.Graphics]::FromImage($canvas)
$titleFont=[System.Drawing.Font]::new('Segoe UI',25,[System.Drawing.FontStyle]::Regular,[System.Drawing.GraphicsUnit]::Pixel)
$footerFont=[System.Drawing.Font]::new('Segoe UI',18,[System.Drawing.FontStyle]::Regular,[System.Drawing.GraphicsUnit]::Pixel)
$titleBrush=[System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#e5edf6'))
$footerBrush=[System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#9cabb8'))
try {
    $graphics.Clear([System.Drawing.ColorTranslator]::FromHtml('#141a20'))
    $graphics.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $items=@(
        @{File='final_dry.png';Label='DRY  /  Wetness 0.0'},
        @{File='final_halfwet.png';Label='HALF WET  /  Wetness 0.5'},
        @{File='final_soaked.png';Label='SOAKED  /  Wetness 1.0'}
    )
    for($i=0;$i -lt $items.Count;$i++) {
        $x=12+$i*576
        $graphics.DrawString($items[$i].Label,$titleFont,$titleBrush,[single]($x+12),[single]15)
        $capture=[System.Drawing.Image]::FromFile((Join-Path $previewRoot $items[$i].File))
        try {
            $destination=[System.Drawing.Rectangle]::new($x,62,560,384)
            $graphics.DrawImage($capture,$destination,100,285,1000,685,[System.Drawing.GraphicsUnit]::Pixel)
        } finally { $capture.Dispose() }
    }
    $graphics.DrawString('Unretouched UE 5.8 captures | Same actor, camera and lighting | Original shirt maps + cloth reference',$footerFont,$footerBrush,[single]24,[single]471)
    $canvas.Save((Join-Path $previewRoot 'comparison.png'),[System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $graphics.Dispose(); $canvas.Dispose(); $titleFont.Dispose(); $footerFont.Dispose(); $titleBrush.Dispose(); $footerBrush.Dispose()
}
Write-Output (Join-Path $previewRoot 'comparison.png')
