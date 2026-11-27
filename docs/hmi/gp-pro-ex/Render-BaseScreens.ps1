param(
    [ValidateRange(320, 3840)][int]$Width = 800,
    [ValidateRange(240, 2160)][int]$Height = 480
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$theme = @{
    background = '#0B1421'; panel = '#142438'; border = '#34516B'
    text = '#EFF5FF'; muted = '#A6B7CE'; cyan = '#66D8EE'; amber = '#F7C875'
}
$menu = [ordered]@{ B100 = '메인'; B200 = '설비'; B300 = '검사·분류'; B400 = '포장·인계'; B500 = '알람' }
$screens = [ordered]@{
    B100 = '메인 운전'; B200 = '설비 관제'; B210 = '검사기 상세'; B220 = '보조 설비 상세'
    B300 = '검사·분류'; B400 = '포장·인계'; B500 = '알람'; B510 = '판정 기준 조회'
}

function Rectangle($x, $y, $w, $h, $fill) {
    $brush = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml($fill))
    try { $graphics.FillRectangle($brush, [single]$x, [single]$y, [single]$w, [single]$h) }
    finally { $brush.Dispose() }
}

function TextLine($value, $x, $y, $size = 13, $color = $theme.text, [switch]$Bold) {
    $style = if ($Bold) { [Drawing.FontStyle]::Bold } else { [Drawing.FontStyle]::Regular }
    $font = [Drawing.Font]::new('Malgun Gothic', [single]$size, $style, [Drawing.GraphicsUnit]::Pixel)
    $brush = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml($color))
    try { $graphics.DrawString($value, $font, $brush, [single]$x, [single]$y) }
    finally { $brush.Dispose(); $font.Dispose() }
}

function Panel($title, $x, $y, $w, $h) {
    Rectangle $x $y $w $h $theme.border
    Rectangle ($x+1) ($y+1) ($w-2) ($h-2) $theme.panel
    TextLine $title ($x+11) ($y+9) 14 $theme.cyan -Bold
}

function FieldGrid($rows, $y = 108) {
    foreach ($row in $rows) {
        Panel $row[0] 18 $y 764 46
        TextLine $row[1] 305 ($y+10) 15 $theme.muted
        $y += 53
    }
}

function DrawMain {
    Panel '2A 공정 평면도' 18 105 764 175
    Rectangle 48 183 704 5 $theme.border
    $codes = @('IN','VIS1','VIS2','T1–T4','IDC','SORT','A/B/C','BOX','OUT')
    $labels = @('투입','ID 판독','외관','전기 검사','ID 확인','분류','특성군','4셀 포장','팩 인계')
    for ($i=0; $i -lt $codes.Count; $i++) {
        $x = 32 + 82*$i
        Rectangle $x 165 69 39 '#1E3550'
        TextLine $codes[$i] ($x+8) 173 15 $theme.text -Bold
        TextLine $labels[$i] ($x+4) 209 12 $theme.muted
    }
    TextLine '↳ RJ1 · 외관 NG' 147 247 13 $theme.amber
    TextLine '↳ RT 재검 → 합류  /  RJ2 최종 NG' 355 247 13 $theme.amber
    $metrics = @('투입 셀','재검 대기','완료 Kit','열린 알람')
    for ($i=0; $i -lt $metrics.Count; $i++) {
        $x = 18 + 194*$i
        Panel $metrics[$i] $x 291 182 69
        TextLine '미수집' ($x+12) 320 18 $theme.muted
    }
    TextLine '운전 조작 미연동' 22 388 14 $theme.amber
    foreach ($action in @(@('START',467),@('STOP',571),@('RESET',675))) {
        Rectangle $action[1] 378 91 39 '#202E40'
        TextLine $action[0] ($action[1]+15) 388 13 $theme.muted
    }
}

function DrawEquipment {
    foreach ($index in 0..4) {
        $name = @('T1','T2','T3','T4','RT')[$index]
        $x = 18 + 154*$index
        Panel $name $x 108 148 83
        TextLine '상태 미수집' ($x+11) 145 14 $theme.muted
    }
    FieldGrid @(@('비전·식별','IN · VIS1 · VIS2 · IDC  /  미수집'),
                @('이송·분류','SORT · LA · LB · LC · RJ1 · RJ2  /  미수집'),
                @('포장·인계','BOX · OUT  /  미수집'),
                @('선택 설비 최근 알람','미수집')) 203
}

function DrawPacking {
    Panel 'A/B/C 레인 · 대기 셀' 18 104 764 57
    TextLine 'A 미수집                 B 미수집                 C 미수집' 32 131 14 $theme.muted
    Panel 'Kit ID —    ·    구성 확인 대기' 18 170 764 108
    for ($i=0; $i -lt 4; $i++) {
        $x = 32 + 187*$i
        Rectangle $x 213 173 44 '#213953'
        TextLine ('슬롯 {0}  ·  미수집' -f ($i+1)) ($x+10) 223 13 $theme.muted
    }
    FieldGrid @(@('팩 라인 인계','포장 → 요청 → 출구 통과 → 수신 확인'),
                @('현재 인계 상태','미수집')) 287
}

$scale = [Math]::Min($Width/800.0, $Height/480.0)
foreach ($screen in $screens.GetEnumerator()) {
    $bitmap = [Drawing.Bitmap]::new($Width, $Height)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.Clear([Drawing.ColorTranslator]::FromHtml($theme.background))
        $graphics.TranslateTransform([single](($Width-800*$scale)/2),[single](($Height-480*$scale)/2))
        $graphics.ScaleTransform([single]$scale,[single]$scale)
        $graphics.TextRenderingHint = [Drawing.Text.TextRenderingHint]::AntiAliasGridFit
        TextLine 'CELLECT / 2A' 18 10 13 $theme.cyan -Bold
        TextLine $screen.Value 18 32 25 $theme.text -Bold
        TextLine '작화 초안 · PLC 미연동' 569 17 15 $theme.amber -Bold
        TextLine '회차 —   /   최근 관측 —' 569 43 13 $theme.muted
        Rectangle 18 75 764 1 $theme.border
        switch ($screen.Key) {
            B100 { DrawMain }
            B200 { DrawEquipment }
            B210 {
                FieldGrid @(@('선택 검사기','T1       T2       T3       T4       RT'),@('상태 / 최근 관측','미수집'),
                    @('Cell ID / 시도 / 진행률','—    /    —    /    미연동'),@('OCV / IR / 결과','— V   /   — mΩ   /   미측정'),
                    @('RT 최초·재검 / 알람','미수집'))
            }
            B220 {
                FieldGrid @(@('선택 설비','IN · VIS1 · VIS2 · IDC · SORT · LA~LC · BOX · OUT'),
                    @('관측 상태 / 시각','미수집'),@('감지 / ID 결과','미수집'),@('레인 진입 / 실제 배출','미수집'),
                    @('슬롯 / 인계','미수집'))
            }
            B300 {
                FieldGrid @(@('Cell ID / LOT','미수집'),@('외관검사','미수집'),@('1차 전기검사','— V   /   — mΩ   /   미측정'),
                    @('재검 / 최종 결과','미수집'),@('전기적 특성군 / 실제 레인','미수집'))
            }
            B400 { DrawPacking }
            B500 {
                FieldGrid @(@('활성 알람 / LOT 보류','미수집'),@('선택 설비 / 발생 시각','미수집'),
                    @('확인 / 원인 해제','미수집'),@('조치 안내','미수집'),@('판정 기준 조회','B510'))
            }
            B510 {
                FieldGrid @(@('OCV 하한 / 상한','— V   /   — V'),@('IR 상한','— mΩ'),
                    @('A/B · B/C 경계','— V   /   — V'),@('LOT 보류 / 재검 한도','— 건   /   — 회'),
                    @('적용 기준 버전','미수집'))
            }
        }
        $active = switch ($screen.Key) { B210 { 'B200' }; B220 { 'B200' }; B510 { 'B500' }; default { $screen.Key } }
        $i = 0
        foreach ($entry in $menu.GetEnumerator()) {
            $x = 18 + $i*154
            $fill = if ($entry.Key -eq $active) { '#1E4460' } else { '#172A40' }
            Rectangle $x 433 148 34 $fill
            TextLine $entry.Value ($x+12) 441 14 $theme.text -Bold
            $i++
        }
        $bitmap.Save((Join-Path $PSScriptRoot ($screen.Key+'.png')), [Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}
