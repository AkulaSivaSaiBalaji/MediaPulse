# MediaPulse — Power BI Relationships & Filter Propagation

## 1. Relational Topology & Cardinality Matrix

All relationships in the MediaPulse semantic model follow single-direction star-schema propagation to prevent ambiguous filter paths, Cartesian explosions, and circular dependencies.

| From Table (Dimension) | Key Column | To Table (Fact / Bridge) | Foreign Key | Cardinality | Filter Direction | State | Security / RLS |
|---|---|---|---|---|---|---|---|
| `DimCategory` | `category_id` | `DimVideo` | `category_id` | 1 : Many (1:*) | Single (`DimCategory` $\rightarrow$ `DimVideo`) | Active | None |
| `DimChannel` | `channel_id` | `DimVideo` | `channel_id` | 1 : Many (1:*) | Single (`DimChannel` $\rightarrow$ `DimVideo`) | Active | None |
| `DimVideo` | `video_id` | `FactTrendingSnapshot` | `video_id` | 1 : Many (1:*) | Single (`DimVideo` $\rightarrow$ `FactTrendingSnapshot`) | Active | None |
| `DimDate` | `full_date` | `FactTrendingSnapshot` | `trending_date` | 1 : Many (1:*) | Single (`DimDate` $\rightarrow$ `FactTrendingSnapshot`) | **Active** | None |
| `DimDate` | `full_date` | `DimVideo` | `publish_date` | 1 : Many (1:*) | Single (`DimDate` $\rightarrow$ `DimVideo`) | **Inactive** | None |

---

## 2. Filter Propagation Mechanics

```mermaid
flowchart TD
    subgraph Dimensions
        Cat[DimCategory]
        Chan[DimChannel]
        Date[DimDate]
    end

    subgraph Intermediate Dimension
        Vid[DimVideo]
    end

    subgraph Fact Table
        Fact[FactTrendingSnapshot]
    end

    Cat -->|1:M (Active)| Vid
    Chan -->|1:M (Active)| Vid
    Vid -->|1:M (Active)| Fact
    Date -->|1:M (Active: trending_date)| Fact
    Date -.->|1:M (Inactive: publish_date)| Vid

    style Cat fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    style Chan fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    style Date fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    style Vid fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    style Fact fill:#fce4ec,stroke:#c2185b,stroke-width:2px;
```

### 1. Primary Filter Path (Trending Snapshot Analysis)
- When a user filters by **Category** or **Channel**:
  - `DimCategory` or `DimChannel` filters `DimVideo` directly.
  - The filtered `DimVideo` rows naturally filter `FactTrendingSnapshot` via the 1:M active relationship on `video_id`.
  - Result: All snapshot observations, views, and interactions for the selected categories/channels are dynamically filtered.
- When a user selects a date on the **Observed Trending Date Slicer**:
  - `DimDate` filters `FactTrendingSnapshot` directly via the active relationship on `trending_date`.
  - Only snapshot rows collected on that date are passed to the visuals.

### 2. Role-Playing Date Dimension (Publication Date Analysis)
- The model avoids creating a redundant `DimPublishDate` table by using an **Inactive Relationship** between `DimDate[full_date]` and `DimVideo[publish_date]`.
- For standard trending performance, `DimDate` acts as the **Trending Observation Date**.
- For upload and cohort analysis, DAX activates the publication date relationship using `USERELATIONSHIP()`:
  ```dax
  Videos Published in Period = 
  CALCULATE(
      [Total Unique Videos],
      USERELATIONSHIP(DimDate[full_date], DimVideo[publish_date])
  )
  ```

---

## 3. Ambiguity & Bidirectional Filtering Justification

### Why Bidirectional Filtering is Strictly Avoided:
1. **Grain Bleed:** Enabling bidirectional filtering between `DimVideo` and `FactTrendingSnapshot` would allow date slicers on `FactTrendingSnapshot` to back-propagate into `DimVideo`, filtering out videos that were published on other dates but trended on the selected date.
2. **Performance Penalty:** In-memory bidirectional joins require expanded table scanning in the VertiPaq engine, slowing down interactive cross-filtering.
3. **Determinism:** Single-direction propagation guarantees that KPI denominators (such as `[Total Unique Videos]`) remain completely predictable and mathematically sound.
