---
title: WB045 DNA Extraction - Extract DNA from the liquid culture
experimenter: Wonjae
created_date: '2025-08-17'
last_updated_date: '2025-08-17'
---

## \[WB045 DNA Extraction\] Extract DNA from the liquid culture

| 이 워크플로의 설명을 간략하게 작성합니다 (아래 설명은 템플릿으로 사용자 목적에 맞도록 수정합니다)
| This workflow focuses on releasing DNA from biological samples (e.g., cultured cells, tissues) through lysis and initial separation from major cellular components like proteins and lipids.

## 🗂️ 관련 유닛오퍼레이션

| 관련된 유닛오퍼레이션 목록을 아래 표시 사이에 입력합니다.
| `F1`, `New HW/SW Unit Operation` 명령 수행시 해당 목록은 표시된 위치 사이에 자동 추가됩니다.

<!-- UNITOPERATION_LIST_START -->

------------------------------------------------------------------------

### \[UHW255 Centrifuge\] Cell down for plasmid prep

-   **Description**: Separating components of different densities within a liquid sample by applying centrifugal force. Used for pelleting cells, clarifying solutions, separating precipitates, and sample preparation steps in various workflows.

#### Meta

-   Experimenter: Wonjae
-   Start_date: '2025-08-17 13:14'
-   End_date: ''

#### Input

-   Incubated colonies with liquid culture (LMP001)

#### Reagent

-   None

#### Consumables

-   None

#### Equipment

-   Plate centrifuge

#### Method

-   Turn on the centrifuge to 3000 rpm and 4℃ temperature
-   Add main culture cell in centrifuge with balance
-   Centrifuge for 10 min
-   Remove supernatant

#### Output

-   Cultured cell without supernatant (LMP001)

## \#### Results & Discussions

------------------------------------------------------------------------

------------------------------------------------------------------------

### \[UHW250 Nucleic Acid Purification\] DNA extraction

-   **Description**: The process of purifying DNA or RNA from biological samples using an automated device. It ensures high purity and yield for downstream applications.

#### Meta

-   Experimenter: Wonjae
-   Start_date: '2025-08-17 13:41'
-   End_date: ''

#### Input

-   Cultured cell without supernatant (LMP001)

#### Reagents

-   Cosmogenetech LaboPass Plasmid Mini prep Kit
    -   S1 buffer (Room #1117, refrigerator #431 4℃)
    -   S2 buffer
    -   S3 buffer
    -   PW buffer
    -   EB buffer

#### Consumables

-   Cosmogenetech LaboPass Plasmid Mini prep Kit
    -   spin column
    -   collection tube
-   reservoir
-   pipette tip
-   1.5mL tube
-   waste bottle
-   paper towel

#### Equipment

-   pipette
-   multi-channel pipette
-   microcentrifuge

#### Method

-   Remove the supernatant using a multi-channel pipette.

-   Add an appropriate volume of S1 buffer to the reservoir, dispense 83 μL into each well with a multi-channel pipette, and pipette up and down for resuspension

    -   Resuspension step (sometimes performed by vortexing)

    -   Components: RNase A (RNA degradation after lysis; added to S1 instead of S2 because RNase A requires cold storage, while SDS in S2 tends to precipitate upon refrigeration), EDTA (chelates divalent cations to destabilize the cell wall), Tris-HCl (maintains neutral pH), glucose (maintains osmotic balance)

-   Add S2 buffer into the reservoir, dispense 83 μL into each well, pipette gently, and incubate for 5 min (pH indicator: white → blue)

    -   Lysis step (do not vortex)

    -   Components: NaOH (denatures chromosomal and plasmid DNA; plasmid DNA remains less denatured due to its supercoiled structure), SDS (disrupts cell membranes and denatures proteins)

-   Add S3 buffer into the reservoir, dispense 117 μL into each well, pipette gently (pH indicator: blue → white)

    -   Neutralization step (do not vortex)

    -   Components: potassium acetate (precipitates proteins, allows renaturation of plasmid DNA)

-   Transfer each sample to a 1.5 mL microcentrifuge tube

-   Centrifuge at 13,000 rpm for 10 min

    -   High-density bacterial chromosomal DNA and proteins form a pellet, while plasmid DNA remains in the supernatant

-   Insert spin columns into collection tubes and label according to sample number

-   Transfer the supernatant to the spin column and incubate for 1 min

    -   Under high-salt conditions, plasmid DNA binds to the membrane

-   Centrifuge at 13,000 rpm for 1 min

-   Discard the flow-through and add 750 μL of PW buffer to each column, followed by centrifugation at 13,000 rpm for 1 min

    -   Wash step

    -   Ethanol (lower polarity than water; DNA remains bound while salts are dissolved)

-   Discard the flow-through and centrifuge again at 13,000 rpm for 1 min

    -   Removes residual PW buffer

-   Transfer the spin column to a clean 1.5 mL microcentrifuge tube

-   Add 40 μL of EB buffer directly to the center of the membrane and incubate for 1 min

    -   Elution step (sometimes performed with distilled water)

-   Centrifuge at 13,000 rpm for 1 min

#### Output

-   Plasmid DNA for long-read sequencing (Sample plasmid #)

#### Results & Discussions

-   (Any results and discussions. Link file path if needed)

------------------------------------------------------------------------

<!-- UNITOPERATION_LIST_END -->