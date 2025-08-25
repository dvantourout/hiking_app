# Météo France Vigilance API Implementation Report

## Executive Summary

This report outlines the implementation strategy for integrating the Météo France Vigilance API into a hiking safety application. The system will alert hikers about dangerous weather phenomena when they regain connectivity, using a Django backend with PostGIS for spatial queries and optimized caching strategies.

## 1. API Overview

### Endpoint Details
- **URL**: `https://public-api.meteofrance.fr/public/DPVigilance/v1/cartevigilance/encours`
- **Authentication**: Required (API key from portail-api.meteofrance.fr)
- **Format**: JSON
- **Update Frequency**: Variable (minimum twice daily at 6h and 16h, more frequent during active weather events)

### Data Structure

#### Response Hierarchy
```
├── product (metadata)
│   ├── update_time (last update timestamp)
│   ├── global_max_color_id (highest alert level across France)
│   └── periods[] (forecast periods)
│       ├── echeance ("J" for today, "J1" for tomorrow)
│       ├── validity times (begin/end)
│       └── timelaps
│           └── domain_ids[] (departments)
│               ├── domain_id (department number)
│               ├── max_color_id (highest alert for department)
│               └── phenomenon_items[] (active phenomena)
│                   ├── phenomenon_id (1-9)
│                   └── timelaps_items[] (timeline)
│                       ├── begin_time
│                       ├── end_time
│                       └── color_id (alert level)
```

#### Alert Levels
| Level | Color | Hex Code | Description | Action Required |
|-------|-------|----------|-------------|-----------------|
| 1 | Green | #31aa35 | No particular vigilance | Normal activity |
| 2 | Yellow | #fff600 | Be attentive | Stay informed |
| 3 | Orange | #ffb82b | Be very vigilant | Prepare for dangerous conditions |
| 4 | Red | #CC0000 | Absolute vigilance | Take emergency protective measures |

#### Weather Phenomena
| ID | Phenomenon | French Name | Hiker Relevance |
|----|------------|-------------|-----------------|
| 1 | Wind | Vent | Critical (orange/red) |
| 2 | Rain-flooding | Pluie-inondation | Important (orange/red) |
| 3 | Thunderstorms | Orages | Critical (all levels) |
| 4 | River floods | Crues | Contextual (near rivers) |
| 5 | Snow-ice | Neige-verglas | Critical (all levels) |
| 6 | Heatwave | Canicule | Important (orange/red) |
| 7 | Extreme cold | Grand froid | Important (orange/red) |
| 8 | Avalanches | Avalanches | Critical (all levels) |
| 9 | Coastal waves | Vagues-submersion | Contextual (coastal trails) |

## 2. Implementation Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    Mobile App                            │
│                 (Hiker Interface)                        │
└────────────────────┬────────────────────────────────────┘
                     │ API Request on Connection
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Django Backend                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              API Layer (DRF)                      │  │
│  │  - User location endpoint                         │  │
│  │  - Vigilance status endpoint                      │  │
│  │  - Push notification service                      │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   │                                      │
│  ┌────────────────▼─────────────────────────────────┐  │
│  │           Business Logic                          │  │
│  │  - Location → Department mapping                  │  │
│  │  - Alert prioritization                          │  │
│  │  - Notification deduplication                    │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   │                                      │
│  ┌────────────────▼─────────────────────────────────┐  │
│  │         Caching Layer (Redis)                     │  │
│  │  - Current vigilance state (5-10 min TTL)        │  │
│  │  - User→Department mappings (1 hour TTL)         │  │
│  │  - Notification history                          │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   │                                      │
│  ┌────────────────▼─────────────────────────────────┐  │
│  │    Data Layer (PostgreSQL + PostGIS)              │  │
│  │  - User location history                          │  │
│  │  - Administrative boundaries                      │  │
│  │  - Vigilance bulletins & history                  │  │
│  └───────────────────────────────────────────────────┘  │
│                   ▲                                      │
└───────────────────┼──────────────────────────────────────┘
                    │
        ┌───────────┴──────────────┐
        │  Scheduled Tasks (Celery) │
        │  - Pull vigilance data    │
        │  - Process notifications  │
        └───────────┬──────────────┘
                    │
                    ▼
        ┌──────────────────────────┐
        │  Météo France API         │
        └──────────────────────────┘
```

### Database Schema

#### Core Tables

**1. User Location History (`user_locations`)**
- Stores GPS coordinates with timestamps
- Includes altitude, accuracy, battery level
- Supports emergency beacon mode (SOS flag)
- Partitioned by month for performance

**2. Administrative Boundaries (`osm_administrative_boundaries`)**
- French departments with geometries
- Simplified geometries for faster queries
- Spatial indexes for point-in-polygon operations
- Expandable to other countries (Spain, Switzerland, Italy)

**3. Vigilance Data**
- `vigilance_bulletins`: Raw API responses with timestamps
- `vigilance_department_status`: Parsed department-level alerts
- `vigilance_phenomena`: Detailed phenomenon timelines
- Historical data for trend analysis

## 3. Data Flow & Processing

### Pull Strategy

#### Dynamic Scheduling
| Condition | Pull Frequency | Rationale |
|-----------|---------------|-----------|
| Normal (all green/yellow) | 30-60 minutes | Low change frequency |
| Active alerts (orange/red) | 15 minutes | Rapid evolution possible |
| Night hours (00h-05h) | 60-90 minutes | Fewer updates expected |
| After update_time change | Immediate + high frequency | Fresh data available |

#### Processing Pipeline
1. **Fetch**: Retrieve JSON from API
2. **Validate**: Check schema and data integrity
3. **Deduplicate**: Compare hash with previous bulletin
4. **Parse**: Extract department and phenomenon data
5. **Store**: Save to database with proper relationships
6. **Cache**: Update Redis with current state
7. **Notify**: Trigger push notifications if needed

### Spatial Query Optimization

#### Department Detection Methods
```python
# Primary: PostGIS point-in-polygon
SELECT department_id 
FROM osm_administrative_boundaries
WHERE ST_Contains(geom_simplified, user_point)

# Border areas: 5km buffer
SELECT DISTINCT department_id
FROM osm_administrative_boundaries
WHERE ST_DWithin(geom, user_point::geography, 5000)

# Trail coverage: All intersecting departments
SELECT DISTINCT department_id
FROM osm_administrative_boundaries
WHERE ST_Intersects(geom, trail_geometry)
```

#### Performance Metrics
| Method | Query Time | Use Case |
|--------|------------|----------|
| Simplified geometry | ~1-5ms | Real-time checks |
| Buffered query | ~5-10ms | Border areas |
| Cached lookup | <1ms | Repeat queries |

## 4. Alert Generation Logic

### Priority Matrix

| Priority | Phenomena | Conditions | Action |
|----------|-----------|------------|--------|
| **Critical** | Thunderstorms, Snow-ice, Avalanches | Any level > green | Immediate notification |
| **Critical** | Wind | Orange/Red only | Immediate notification |
| **Important** | Rain-flooding, Extreme temps | Orange/Red only | Batched notification |
| **Contextual** | River floods, Coastal waves | Location-dependent | Conditional notification |

### Notification Intelligence

#### Deduplication Rules
- Unique key: `{user_id}:{dept_id}:{phenomenon_id}:{color_id}:{period}`
- Cool-down period: 3 hours minimum between same-level alerts
- Escalation override: Immediate notification if danger level increases

#### Message Construction
```
⚠️ ALERT LEVEL - Department Name (XX)
Valid: DD/MM HHh - DD/MM HHh

Active Dangers:
🌩️ PHENOMENON - Level (HHh-HHh)
[Additional phenomena...]

Timeline:
• Current: [Status]
• Coming: [Evolution]

Recommendation: [Safety advice]
```

## 5. Caching Strategy

### Multi-Tier Architecture

| Layer | Technology | TTL | Content |
|-------|-----------|-----|---------|
| L1 - Hot | Redis | 5-10 min | Current vigilance state |
| L2 - Warm | PostgreSQL | 48 hours | Recent bulletins |
| L3 - Cold | PostgreSQL (partitioned) | 1 year | Historical data |

### Cache Keys Structure
```
vigilance:current:{update_time}     # Global state
vigilance:dept:{dept_id}:{period}   # Department specific
vigilance:user:{user_id}:relevant   # User's departments
notification:sent:{hash}            # Deduplication tracking
```

## 6. Performance Considerations

### Optimization Strategies

1. **Spatial Indexes**
   - GIST index on simplified geometries
   - Covering index for user locations
   - Partial index for active vigilance

2. **Database Partitioning**
   - User locations by month
   - Vigilance bulletins by quarter
   - Automatic partition management

3. **Query Optimization**
   - Materialized views for current state
   - Prepared statements for frequent queries
   - Connection pooling

### Expected Performance

| Operation | Target Time | Scale |
|-----------|------------|-------|
| User location → Department | <10ms | 10K concurrent users |
| Vigilance state retrieval | <5ms | From cache |
| Bulk notification processing | <1s | 1000 users/department |
| API data pull & processing | <2s | Complete update |

## 7. Scalability & Reliability

### Failure Handling

| Failure Type | Response Strategy |
|--------------|------------------|
| API timeout | Retry with exponential backoff |
| Invalid data | Log error, use last known good |
| Database overload | Fallback to cache |
| Redis unavailable | Direct database queries |

### Monitoring Points

- API response times and error rates
- Cache hit ratios
- Database query performance
- Notification delivery success rate
- User location update frequency

### Scaling Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| API latency | >1s average | Increase cache TTL |
| DB CPU | >70% sustained | Add read replicas |
| Redis memory | >80% | Increase instance size |
| Queue depth | >1000 | Add Celery workers |

## 8. Future Enhancements

### Phase 1 (Current)
- ✅ Basic API integration
- ✅ Department-level alerts
- ✅ Push notifications
- ✅ Location tracking

### Phase 2 (3 months)
- Trail-specific alerts
- Multi-country support (Spain, Switzerland, Italy)
- Weather forecast integration
- Offline data caching

### Phase 3 (6 months)
- Predictive alerts based on movement
- Crowd-sourced condition reports
- Alternative route suggestions
- Historical pattern analysis

### Phase 4 (12 months)
- Machine learning for personalized alerts
- Integration with rescue services
- Real-time hazard mapping
- Community alert sharing

## 9. Security & Privacy

### Data Protection
- Location data encrypted at rest
- GDPR-compliant data retention
- User consent for tracking
- Anonymous mode option

### API Security
- Rate limiting per user
- API key rotation schedule
- Request signature validation
- IP allowlisting for production

## 10. Cost Estimation

### Infrastructure Costs (Monthly)

| Component | Specification | Estimated Cost |
|-----------|--------------|----------------|
| Django Server | 2 vCPU, 4GB RAM | €40 |
| PostgreSQL | 20GB SSD, backups | €30 |
| Redis | 2GB RAM | €15 |
| API calls | ~50K/day | Free (public API) |
| Push notifications | ~10K/day | €20 |
| **Total** | | **€105/month** |

### Development Timeline

| Phase | Duration | Resources |
|-------|----------|-----------|
| Initial setup | 2 weeks | 1 developer |
| Core implementation | 4 weeks | 1 developer |
| Testing & optimization | 2 weeks | 1 developer + QA |
| Deployment | 1 week | DevOps support |
| **Total** | **9 weeks** | |

## Conclusion

The Météo France Vigilance API integration provides a robust foundation for hiker safety alerts. The architecture balances real-time performance with data persistence, enabling both immediate notifications and historical analysis. The system is designed to scale horizontally and can be extended to support additional countries and weather services.

Key success factors:
- Efficient spatial queries using PostGIS
- Multi-tier caching for performance
- Smart notification deduplication
- Extensible schema for multi-country support
- Comprehensive monitoring and failure handling

This implementation will significantly enhance hiker safety by providing timely, relevant weather alerts when connectivity is available, potentially preventing dangerous situations in mountainous and remote areas.