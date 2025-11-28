# Non Functional Requirements [System's interests]

## Accessibility

- [ ] The system should allow access from the Bajeti Website
- [ ] The system should allow the creation of Categories and Expenses using Siri commands like "Create New Expense" Command that can create a Shortcut in Iphones

## CAP Theorem

You can only have two options from the options below

- Consistency
- Availability
- Partition Tolerance

- [ ] The system API should be available at all times duirng the day in East Africa

## Scalability

How the application scales and evolves as the application grows

## Security

How protected should the data be

- [ ] The system should provide secure access to user's data
- [ ] The system should provide secure access to the API

## Durability

Think about how important the data is and what it would mean in case of data loss

- [ ] The system should ensure the data is persistent
- [ ] The system should ensure the data is replicated remotely

## Latency

Think about how quickly the data should be provided

- [ ] The system should provide latency of < 3ms

## Fault tolerance

Think about recovery mechanisms, failover and redundancy

- [ ] The system should provide a notification if services are offline

## Dashboard

- [ ] The system should provide information on the logging metrics
- [ ] The system should provide monitoring information on the system's health
- [ ] The system should provide alerts and notifications on the status of the system

## READ/WRITE Operations

- [ ] The system performs more read operations than write operations
