import kr.dogfoot.hwplib.object.HWPFile;
import kr.dogfoot.hwplib.object.bindata.EmbeddedBinaryData;
import kr.dogfoot.hwplib.object.bodytext.ParagraphListInterface;
import kr.dogfoot.hwplib.object.bodytext.Section;
import kr.dogfoot.hwplib.object.bodytext.control.Control;
import kr.dogfoot.hwplib.object.bodytext.control.ControlTable;
import kr.dogfoot.hwplib.object.bodytext.control.ControlType;
import kr.dogfoot.hwplib.object.bodytext.control.gso.ControlPicture;
import kr.dogfoot.hwplib.object.bodytext.control.table.Cell;
import kr.dogfoot.hwplib.object.bodytext.control.table.Row;
import kr.dogfoot.hwplib.object.bodytext.paragraph.Paragraph;
import kr.dogfoot.hwplib.object.docinfo.BinData;
import kr.dogfoot.hwplib.reader.HWPReader;
import kr.dogfoot.hwplib.writer.HWPWriter;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.nio.file.Files;
import java.util.List;

/**
 * Builds the 2A (Cellect) project plan (hwp) on top of a plan document that uses the course form.
 *
 * The template is the course-form plan the instructor pointed to as a good layout (1조a).
 * Its cover, heading styles, table styles and page setup are kept; every text, table row
 * and picture is replaced with 2A content. Paragraph numbers (P[n]) refer to the template.
 *
 * Usage: java -cp "<classes>;hwplib-1.1.11.jar" BuildPlan template.hwp out.hwp docs/assets/hwp
 */
public class BuildPlan {
    static HWPFile f;
    static Section s;
    static Paragraph[] P;
    static File figs;

    // ---------- helpers ----------

    /** Replace a paragraph's text, keeping its first character shape. Hangul re-flows lines on open. */
    static void set(Paragraph p, String text) throws Exception {
        long cs = p.getCharShape().getPositonShapeIdPairList().get(0).getShapeId();
        p.deleteText();
        if (!text.isEmpty()) {
            p.createText();
            p.getText().addString(text);
        }
        p.deleteCharShape();
        p.createCharShape();
        p.getCharShape().addParaCharShape(0, cs);
        p.deleteLineSeg();
        p.deleteRangeTag();
        p.getHeader().setCharacterCount(text.length() + 1);
        p.getHeader().setCharShapeCount(1);
        p.getHeader().setLineAlignCount(0);
        p.getHeader().setRangeTagCount(0);
    }

    static void set(int i, String text) throws Exception { set(P[i], text); }

    /** Fill a cell with one paragraph per line ("\n" separated). Extra lines clone the first paragraph. */
    static void cell(Cell c, String value) throws Exception {
        String[] lines = value.split("\n");
        ParagraphListInterface pl = c.getParagraphList();
        Paragraph proto = pl.getParagraph(0);
        for (int i = 0; i < lines.length; i++) {
            if (i >= pl.getParagraphCount()) pl.insertParagraph(pl.getParagraphCount(), proto.clone());
            set(pl.getParagraph(i), lines[i]);
        }
        while (pl.getParagraphCount() > lines.length) pl.deleteParagraph(pl.getParagraphCount() - 1);
        c.getListHeader().setParaCount(lines.length);
        for (int i = 0; i < pl.getParagraphCount(); i++) pl.getParagraph(i).getHeader().setLastInList(i == lines.length - 1);
    }

    static ControlTable table(int i) {
        for (Control c : P[i].getControlList()) if (c.getType() == ControlType.Table) return (ControlTable) c;
        throw new RuntimeException("no table in P" + i);
    }

    /** Rewrite a whole table (header row included). Rows beyond the content are removed. */
    static void fill(int i, String[][] rows) throws Exception {
        ControlTable t = table(i);
        if (rows.length > t.getRowList().size()) throw new RuntimeException("P" + i + ": template table has only " + t.getRowList().size() + " rows");
        long removed = 0;
        while (t.getRowList().size() > rows.length) {
            Row r = t.getRowList().remove(t.getRowList().size() - 1);
            removed += r.getCellList().get(0).getListHeader().getHeight();
            List<Integer> cc = t.getTable().getCellCountOfRowList();
            cc.remove(cc.size() - 1);
        }
        t.getTable().setRowCount(rows.length);
        t.getHeader().setHeight(t.getHeader().getHeight() - removed);
        for (int r = 0; r < rows.length; r++) {
            List<Cell> cells = t.getRowList().get(r).getCellList();
            if (cells.size() != rows[r].length) throw new RuntimeException("P" + i + " row " + r + ": " + cells.size() + " cells, content has " + rows[r].length);
            for (int k = 0; k < cells.size(); k++) cell(cells.get(k), rows[r][k]);
        }
    }

    static String binName(int id, String ext) { return String.format("BIN%04X.%s", id, ext); }

    static EmbeddedBinaryData embedded(int id) {
        for (EmbeddedBinaryData e : f.getBinData().getEmbeddedBinaryDataList())
            if (e.getName().toUpperCase().startsWith(binName(id, "").toUpperCase())) return e;
        throw new RuntimeException("no embedded data for bin " + id);
    }

    static void putPng(int id, byte[] png) {
        for (BinData b : f.getDocInfo().getBinDataList()) if (b.getBinDataID() == id) b.setExtensionForEmbedding("png");
        EmbeddedBinaryData e = embedded(id);
        e.setName(binName(id, "png"));
        e.setData(png);
    }

    /** Swap the picture in paragraph i for a PNG, full text width, height from the image ratio. */
    static void picture(int i, String file, long width) throws Exception { picture(P[i], file, width); }

    static void picture(Paragraph para, String file, long width) throws Exception {
        ControlPicture pic = null;
        for (Control c : para.getControlList()) if (c instanceof ControlPicture) pic = (ControlPicture) c;
        if (pic == null) throw new RuntimeException("no picture in paragraph");
        File src = new File(figs, file);
        BufferedImage img = ImageIO.read(src);
        long height = Math.round(width * (double) img.getHeight() / img.getWidth());
        putPng(pic.getShapeComponentPicture().getPictureInfo().getBinItemID(), Files.readAllBytes(src.toPath()));
        pic.getHeader().setWidth(width);
        pic.getHeader().setHeight(height);
        var sc = pic.getShapeComponent();
        sc.setWidthAtCreate((int) width);
        sc.setHeightAtCreate((int) height);
        sc.setWidthAtCurrent((int) width);
        sc.setHeightAtCurrent((int) height);
        sc.setRotateXCenter((int) (width / 2));
        sc.setRotateYCenter((int) (height / 2));
        var p = pic.getShapeComponentPicture();
        p.getLeftTop().setX(0); p.getLeftTop().setY(0);
        p.getRightTop().setX(width); p.getRightTop().setY(0);
        p.getLeftBottom().setX(0); p.getLeftBottom().setY(height);
        p.getRightBottom().setX(width); p.getRightBottom().setY(height);
        p.setLeftAfterCutting(0); p.setTopAfterCutting(0);
        p.setRightAfterCutting((int) width); p.setBottomAfterCutting((int) height);
        p.setImageWidth(width);
        p.setImageHeight(height);
    }

    /** Pictures we drop still have a BinData entry; blank them so no template image stays in the file. */
    static void blankPicture(int i) throws Exception {
        for (Control c : P[i].getControlList())
            if (c instanceof ControlPicture && ((ControlPicture) c).getShapeComponentPicture().getPictureInfo().getBinItemID() != 3) {
                BufferedImage dot = new BufferedImage(1, 1, BufferedImage.TYPE_INT_RGB);
                dot.setRGB(0, 0, 0xFFFFFF);
                ByteArrayOutputStream out = new ByteArrayOutputStream();
                ImageIO.write(dot, "png", out);
                putPng(((ControlPicture) c).getShapeComponentPicture().getPictureInfo().getBinItemID(), out.toByteArray());
            }
    }

    static int indexOf(Paragraph p) {
        for (int i = 0; i < s.getParagraphCount(); i++) if (s.getParagraph(i) == p) return i;
        throw new RuntimeException("paragraph not found");
    }

    static void delete(int... idx) throws Exception {
        for (int i : idx) {
            if (P[i].getControlList() != null) blankPicture(i);
            s.deleteParagraph(indexOf(P[i]));
        }
    }

    static void deleteRange(int from, int to) throws Exception {
        for (int i = from; i <= to; i++) delete(i);
    }

    static void pageBreak(int i, boolean on) { P[i].getHeader().getDivideSort().setDividePage(on); }

    static final long FULL = 48189;   // text width of the template (HWPUNIT)

    // ---------- content ----------

    public static void main(String[] a) throws Exception {
        f = HWPReader.fromFile(a[0]);
        s = f.getBodyText().getSectionList().get(0);
        P = s.getParagraphs().clone();
        figs = new File(a[2]);

        // Cover
        set(12, "【 과제명 : 배터리 셀 입고검사·매칭 공급 라인 디지털 트윈 】");
        fill(18, new String[][]{
            {"교과목명", "[인텔] AI 융합 DX 마스터 클래스"},
            {"지도교수", "김 유 성"},
            {"팀 구분", "Cellect (2A)"},
            {"팀    장", "최예현"},
            {"팀    원", "이순필, 박해준, 정연우, 김동혁"}});
        fill(23, new String[][]{{"배터리 셀 입고검사·매칭 공급 라인 프로젝트 계획서"}});
        Paragraph mark = P[22].clone();
        for (Control c : mark.getControlList())
            if (c instanceof ControlPicture) {
                ControlPicture pic = (ControlPicture) c;
                pic.getShapeComponentPicture().getPictureInfo().setBinItemID(3);   // spare: step pictures are dropped
                long id = System.nanoTime() & 0x7fffffffL;
                pic.getHeader().setInstanceId(id);
                pic.getShapeComponentPicture().setInstanceId(id + 1);
            }
        picture(mark, "../cellect-wordmark.png", 14000);
        s.insertParagraph(indexOf(P[13]) + 1, mark);
        delete(14, 15, 16);

        // 1. 프로젝트 개요
        set(26, "   배터리 조립·검사 설비 앞단에서 셀 입고, 검사, NG 분리, 전압 구간 분류, 4셀 세트 공급으로 이어지는 가상 전공정을 Factory I/O로 만들고, PLC와 SCADA로 제어하고 감시하는 자동화 프로젝트를 계획하고 구현하여 시스템 상호 운용 능력을 향상하고자 함.");
        fill(28, new String[][]{
            {"항목", "내용"},
            {"과제명", "배터리 셀 입고검사·매칭 공급 라인 디지털 트윈"},
            {"기간", "2026. 11. 17 (화) ~ 12. 01 (화), 수업일 10일"},
            {"팀 · 인원", "Cellect (Cell + Select) · 2A, 5명 (SCADA 1 · 래더 2 · Factory I/O 1 · 실측·시험 1)"},
            {"제어 환경", "Mitsubishi Q03UDE (GX Works2), Factory I/O v2.5"},
            {"통신", "시연: Modbus TCP 브리지 / 실물 PLC 연계: OPC 서버 경유 (11/19 확정)"},
            {"다루는 품목", "18650 셀 (LOT 3종) → 같은 전압 구간 4셀 세트"},
            {"결과물", "자동 운전 시연, 래더 · Factory I/O 씬 · SCADA, I/O 리스트, 발표 자료"}});
        fill(30, new String[][]{
            {"문제", "해결 방법"},
            {"들어온 순서대로 4개씩 묶여 세트 안 셀 전압 편차가 큼", "전압 구간(A · B · C)별 버퍼에 모았다가 같은 구간 4개씩 공급"},
            {"불량 셀이 조립 설비로 넘어갈 위험", "검사 위치에서 셀마다 판정, NG는 푸셔로 격리 레인에 배출"},
            {"한 LOT에서 불량이 반복돼도 계속 공급됨", "LOT별 NG 누계가 3건이면 그 LOT 공급 보류, 알람"},
            {"셀 · 세트 이력이 공정 사이에서 끊김", "셀 ID · 세트 ID를 DB에 기록하고 2B(후공정)로 인계"},
            {"조립 설비가 준비 안 됐는데 세트가 넘어감", "준비 · 공급 요청 · 수신 확인 신호로 인터록"}});

        // 2. 프로젝트 목표
        set(34, "     (1) 구역별 스텝 방식 래더로 입고 · 검사 · 분류 · 공급 시퀀스 구현");
        set(35, "     (2) 시프트 레지스터로 셀 ID · LOT · 전압을 위치별로 추적");
        set(36, "     (3) Factory I/O · PLC · SCADA 태그 연동과 조립 설비 인터록 설계");
        set(38, "     (4) 전압 구간 버퍼, 4셀 세트 공급, LOT 보류 로직 구현");
        set(42, "     (2) Failure Injection으로 비정상 상황 8건 재현 · 검증 및 보완");
        fill(45, new String[][]{
            {"확인 기준", "내용"},
            {"편차 감소", "같은 셀 데이터로 순서대로 묶은 세트 대비 세트 안 전압 편차 50% 이상 감소 (잠정)"},
            {"분류", "판정 구간과 실제 진입 레인 일치, 100셀 중 오류 0건"},
            {"NG 차단", "NG · 보류 LOT 셀의 공급 유출 0건"},
            {"추적", "공급된 세트의 셀 ID 4개와 DB 기록 일치 100%"},
            {"비정상 대응", "비정상 상황 8건 모두 기대 동작과 일치"}});

        // 3. 프로젝트 계획 - 1) 역할
        fill(49, new String[][]{
            {"구분", "성명", "역할", "담당 범위", "주요 산출물"},
            {"팀장", "최예현", "SCADA · 프로젝트 관리", "통신 브리지, 수집기, DB, 조회 화면, 일정 관리", "브리지 프로그램, DB 테이블 정의, 화면 정의서"},
            {"팀원", "정연우", "래더 A", "Z4 · Z5 (분류 · 버퍼 · 세트 공급), LOT 보류, 조립 설비 연계", "디바이스 맵, 알람 코드표, Z4 · Z5 래더"},
            {"팀원", "이순필", "래더 B", "Z1 ~ Z3 (입고 · 검사 · NG 분리), 셀 추적", "추적 구조 정의, Z1 ~ Z3 래더"},
            {"팀원", "박해준", "Factory I/O", "씬 배치, 태그 연결, 고장 주입", "씬 파일, I/O 매핑표, 고장 주입 절차"},
            {"팀원", "김동혁", "실측 · 시험", "셀 전압 실측, 시험 기록, 문서", "실측 데이터, 시험 기록표, 보고서"},
            {"전원", "-", "공동", "비정상 상황 시험, 통합 실행(매일)", "발표 자료"}});
        set(50, "※ 역할은 기존 배정안 기준이며 팀 회의에서 확정합니다. 구역마다 쓰는 사람은 1명이고, 구역 사이는 요청 · 완료 비트로 주고받습니다.");

        // 2) 공정과정
        fill(54, new String[][]{
            {"구역", "하는 일", "주요 설비 (Factory I/O)", "래더", "실물 연계"},
            {"Z1 입고 · LOT", "셀 투입, ID 부여, 비전으로 LOT 판독", "Emitter, Belt Conveyor, Vision Sensor", "B", "-"},
            {"Z2 검사 · 판정", "검사 위치 정지, 전압 · 내부저항 연결, 합격 · 구간 판정", "Stop Blade, Diffuse Sensor", "B", "실측 전압"},
            {"Z3 NG 분리", "NG · 보류 LOT 셀 배출, LOT별 NG 누계", "Pusher, Capacitive Sensor, Chute", "B", "-"},
            {"Z4 분류 · 버퍼", "A · B · C 레인 분류, 레인별 재고 관리", "Pusher ×3, Belt Conveyor ×3, Stop Blade ×3", "A", "-"},
            {"Z5 세트 공급", "같은 구간 4셀 배출, 출구 확인", "Belt Conveyor, Diffuse Sensor, Remover", "A", "준비 · 수신 확인"}});
        fill(57, new String[][]{
            {"품목", "종류", "구분값", "Vision 코드", "비고"},
            {"셀 (입고)", "파랑 · 초록 · 금속", "LOT 1 · 2 · 3", "1 · 4 · 7", "Raw Material로 표현"},
            {"합격 셀", "A · B · C 구간", "전압 구간", "-", "구간별 버퍼 레인"},
            {"NG 셀", "기준 이탈, LOT 미판독", "-", "-", "격리 레인"},
            {"보류 셀", "NG 누계 3건 LOT", "-", "-", "공급 차단"},
            {"4셀 세트", "같은 구간 셀 4개", "세트 ID", "-", "조립 설비로 공급"}});
        set(58, "※ 전압 · 내부저항은 Factory I/O에 없는 값이라 PLC 데이터 레지스터로 넣습니다. 지금은 임시값이고 실물 셀 실측값으로 바꿉니다. 구간 경계는 실측 분포를 보고 정합니다.");
        set(59, "     (3) 전체 공정 흐름");
        pageBreak(59, false);
        picture(60, "fig-process.png", FULL);
        set(61, "실선 화살표 = 셀 흐름 · 파란 상자 = 버퍼 · 공급 구역 · Z3 = 검사에서 갈라지는 NG 격리");
        set(62, "     (4) 공정별 진행 방법");
        set(63, "※ 번호는 진행 순서입니다. 신호 이름은 Factory I/O 태그 이름이고, PLC 주소는 11/19 I/O 리스트 확정 때 정합니다.");

        String[] head = {"구분", "내용"};
        set(64, "       ① 셀 입고 · LOT 판독 (Z1 · 래더 B)");
        fill(66, new String[][]{head,
            {"사용 설비", "Emitter, Entry Conveyor, Vision Sensor, Diffuse Sensor"},
            {"확인 신호", "Cell arrived, LOT vision (1 파랑 · 4 초록 · 7 금속, 0 = 없음)"},
            {"구동 신호", "Emit cell, Entry conveyor, Main conveyor"},
            {"운전 규칙", "• 앞 셀이 검사 위치를 떠난 뒤에만 다음 셀 투입\n• 비전 값이 0이면 LOT 미판독으로 기록\n• 버퍼 레인이 모두 차면 투입 정지"}});
        set(68, "       ② 검사 · 판정 (Z2 · 래더 B)");
        fill(70, new String[][]{head,
            {"사용 설비", "Stop Blade (검사 위치), Diffuse Sensor"},
            {"확인 신호", "At inspection, 셀 전압 · 내부저항 표 (데이터 레지스터)"},
            {"구동 신호", "Inspection stop, Main conveyor"},
            {"운전 규칙", "• 도착하면 셀 ID 부여, 전압 · 내부저항 값 연결\n• 기준 이탈 · 값 없음 · LOT 미판독 · 보류 LOT는 NG\n• 합격 셀은 전압으로 A · B · C 구간 결정\n• 목적지 레인에 자리가 있고 분류 구간이 비었을 때만 블레이드 해제"}});
        set(72, "       ③ NG 분리 · LOT 보류 (Z3 · 래더 B)");
        pageBreak(72, false);
        fill(74, new String[][]{head,
            {"사용 설비", "Pusher (NG), Capacitive Sensor, Chute, Remover"},
            {"확인 신호", "At pusher NG, Pusher NG front / back"},
            {"구동 신호", "Pusher NG, Main conveyor (미는 동안 정지)"},
            {"운전 규칙", "• NG 셀이 푸셔 앞에 오면 밀어서 격리 레인으로 배출\n• 푸셔 전진 · 복귀 끝 센서로 완료 확인\n• 같은 LOT NG 누계 3건이면 그 LOT 보류, 대기 중인 셀도 공급 차단"}});
        set(76, "       ④ 구간 분류 · 버퍼 (Z4 · 래더 A)");
        fill(78, new String[][]{head,
            {"사용 설비", "Pusher ×3 (A · B · C), Belt Conveyor ×3 (레인), Stop Blade ×3 (레인 끝)"},
            {"확인 신호", "At pusher A · B · C, Pusher front / back"},
            {"구동 신호", "Pusher A · B · C, Lane A · B · C conveyor, Lane A · B · C stop"},
            {"운전 규칙", "• 판정 구간과 같은 레인의 푸셔만 동작\n• 레인별 예약 수 · 실제 재고 관리, 4개가 차면 더 받지 않음\n• 푸셔가 20초 안에 복귀하지 않으면 이상 정지"}});
        set(80, "       ⑤ 4셀 세트 공급 (Z5 · 래더 A)");
        pageBreak(80, false);
        fill(82, new String[][]{head,
            {"사용 설비", "Supply Conveyor, Diffuse Sensor, Chute, Remover (조립 설비로 인계)"},
            {"확인 신호", "Set at exit, 조립 설비 준비 · 수신 확인"},
            {"구동 신호", "Lane stop 해제, Supply conveyor, 세트 공급 요청 · 세트 ID"},
            {"운전 규칙", "• 같은 구간 4개가 모이고 조립 설비가 준비됐을 때만 한 레인씩 배출\n• 출구에서 4개를 세고 수신 확인을 받아야 다음 세트\n• 공급 직전 LOT 보류 여부 다시 확인"}});

        // (5) 시스템 구성도
        picture(97, "fig-system.png", FULL);
        fill(98, new String[][]{
            {"연결 구간", "방식", "주고받는 데이터"},
            {"Factory I/O ↔ PLC", "Modbus TCP 브리지 (시연)\nOPC 서버 (실물 PLC 연계 시)", "센서 입력 → PLC, PLC 출력 → 구동기"},
            {"조립 · 검사 설비 ↔ PLC", "공용 PLC 디바이스 (협의)", "실측 전압, 준비 · 공급 요청 · 수신 확인"},
            {"PLC → SCADA", "Python 수집기", "셀 · 세트 상태, 재고, 알람, 공급 이벤트"},
            {"SCADA ↔ 2B", "공용 DB (협의)", "세트 ID · 셀 ID · LOT · 검사 결과"}});

        // 3) 제어설비
        fill(112, new String[][]{
            {"구분", "설비 · 규격", "수량", "비고"},
            {"PLC", "Mitsubishi Q03UDE", "1", "조립 설비와 공용 (예정)"},
            {"시뮬레이터", "Factory I/O v2.5 Modbus & OPC Edition", "1", "가상 전공정"},
            {"반송", "Belt Conveyor", "6", "입고 1, 메인 1, 레인 3, 공급 1"},
            {"분류 · 정지", "Pusher, Stop Blade", "4 · 4", "NG · A · B · C, 검사 위치 · 레인 끝"},
            {"검출", "Diffuse · Capacitive Sensor, Vision Sensor", "7 · 1", "위치 · 출구 감지, LOT 판독"},
            {"투입 · 회수", "Emitter, Remover, Chute", "1 · 2 · 2", "셀 투입, NG · 공급 회수"},
            {"조작", "Start · Stop · Reset, Emergency Stop", "1식", "조작반"},
            {"실측", "18650 셀, 1차 검사기 (조립 · 검사 설비)", "확인 후 결정", "전압 실측"}});
        fill(116, new String[][]{
            {"구분", "도구", "용도"},
            {"PLC", "GX Works2", "래더(스텝 방식) 작성 · 실행"},
            {"통신", "Python 브리지 (Modbus TCP), OPC 서버 (예정)", "PLC ↔ Factory I/O"},
            {"SCADA", "Python 수집기 + 웹 화면, SQLite", "상태 · 재고 · 이력 · 알람 조회"},
            {"협업", "GitHub, 공유 태그맵", "매일 통합 실행"},
            {"문서", "한글(hwp)", "계획서 · 보고서"}});
        picture(120, "fig-factoryio.png", FULL);
        set(122, "그림 1. 전공정 라인 전체 배치 (Factory I/O, 작업 중)");
        delete(125, 126);
        picture(127, "fig-layout.png", FULL);
        set(128, "그림 2. 구역 배치 (입고 · 검사 · 분류 · 버퍼 · 공급)");

        // 4) 비정상 상황 시험 계획
        set(129, "  4) 비정상 상황 시험 계획 (8건)");
        fill(130, new String[][]{
            {"No", "상황", "재현 방법", "기대 동작", "래더 담당"},
            {"1", "센서 신호 안 들어옴", "Failure Injection: Always Off", "타임아웃 알람, 해당 구역 정지", "이순필"},
            {"2", "센서가 계속 켜짐", "Failure Injection: Always On", "잔류 감지 알람, 다음 투입 금지", "이순필"},
            {"3", "셀 걸림(잼)", "컨베이어 · 레인 위 셀 정체", "해당 구역 정지, 상류 대기", "정연우"},
            {"4", "비상정지", "Emergency Stop 누름", "전 구역 정지 → 리셋 → 재기동", "정연우"},
            {"5", "레인 가득 참", "공급 없이 한 구간 셀만 연속 투입", "그 구간 셀 투입 대기, 비면 재개", "정연우"},
            {"6", "LOT 불량 반복", "한 LOT에 NG 값 3건 주입", "그 LOT 보류, 대기 셀 공급 차단, 알람", "정연우"},
            {"7", "조립 설비 미준비", "준비 신호 OFF", "세트 공급 대기, 배출하지 않음", "정연우"},
            {"8", "통신 끊김", "브리지 강제 종료", "하트비트 감시로 전 구역 정지, 재연결 후 복구", "이순필"}});
        set(131, "※ 재현 환경은 박해준(Factory I/O)이 준비하고, 결과는 최예현(SCADA)이 알람 이력으로 확인합니다. 김동혁이 시험 기록표에 결과를 남깁니다.");

        // 4. 프로젝트 추진일정
        picture(136, "fig-schedule.png", FULL);
        fill(138, new String[][]{
            {"기간", "관문", "래더 (정연우 · 이순필)", "Factory I/O · 실측 (박해준 · 김동혁)", "SCADA (최예현)"},
            {"11/17~11/19", "G1 설계 확정", "디바이스 맵, 공통 시퀀스 골격, 알람 코드표, 추적 구조", "씬 배치 초안, I/O 매핑표, 실물 셀 전압 실측", "브리지 1점 연결 시험, DB 테이블"},
            {"11/23~11/25", "G2 구역 단독 동작", "입고 · 검사 · NG / 분류 · 버퍼 래더", "씬 전체 배치 · 태그 이름, 센서 · 블레이드 · 푸셔 확인", "수집기, 상태 화면"},
            {"11/26~11/27", "G3 전체 연결", "세트 공급 · LOT 보류 · 조립 설비 신호", "편차 비교 첫 측정", "이력 저장 · 조회 화면"},
            {"11/30", "시험 · 기능 동결", "비정상 상황 8건 시험 · 수정", "재현 환경, 측정 반복", "알람 이력 확인"},
            {"12/1", "발표", "시운전, 래더 설명", "Factory I/O 시연, 측정 결과", "SCADA 시연"}});
        set(139, "※ 매일 수업 끝에 래더 · 씬 · 브리지를 합쳐 한 번 돌려 봅니다. 11/19 이후 태그 이름 · 주소 변경은 담당자 합의 후에만 합니다.");

        // 5. 주요 위험과 대응
        fill(142, new String[][]{
            {"위험", "영향", "대응"},
            {"통신 지연", "짧은 센서 신호를 놓치거나 정지 위치가 밀림", "판단 지점마다 블레이드로 세운 뒤 확인, 첫날 왕복 지연 측정"},
            {"한 구간 쏠림", "한 구간 셀만 계속 오면 그 레인이 차서 라인이 멈춤", "레인이 차면 그 구간 투입 대기, 구간 경계를 실측 분포로 조정"},
            {"추적 어긋남", "셀 하나가 빠지면 이후 ID가 한 칸씩 밀림", "검사 위치와 출구에서 셀 수와 ID를 다시 맞춤"},
            {"실측 데이터 부족", "셀 수가 적어 편차 비교가 약해짐", "실측값을 반복 사용한 시험과 실측 비교를 나눠 보고"},
            {"일정 부족", "11/26~11/27 통합에 문제가 몰림", "구역별 최소 목표를 먼저 끝내고, 늦으면 DB · 화면부터 단순화"}});

        // Template parts 2A does not use: step pictures, steps ⑥~⑧, (7) state diagram, a wrapped goal line.
        delete(37);
        delete(65, 69, 73, 77, 81);
        deleteRange(83, 95);
        delete(101, 102, 103);   // (6) I/O · 디바이스 할당 -> design-notes.md
        delete(104, 105, 106);

        HWPWriter.toFile(f, a[1]);
        System.out.println("written " + a[1]);
    }
}
